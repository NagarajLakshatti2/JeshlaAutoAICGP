"""Local slash commands: selected scope, saved observations, no implicit action."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.runtime.chat_shortcuts import is_shortcut, local_shortcut_reply, parse_shortcut
from agent.runtime.turns import run_turn
from agent.storage.chats import ChatCatalog


class ShortcutParserTests(unittest.TestCase):
    def test_existing_slash_continuation_aliases_keep_their_own_handler(self):
        from agent.runtime.continuations import command
        for text in ('/continue', '/continue answer', '/CONTINUE answer!'):
            with self.subTest(text=text):
                self.assertEqual(command(text), 'continue')
                self.assertFalse(is_shortcut(text))
                self.assertIsNone(parse_shortcut(text))

    def test_normal_messages_and_filesystem_paths_are_not_commands(self):
        for text in ('hello', 'Explain /read', '/* Java comment */', '/tmp/file.txt', r'D:\project\file.py', '/api/v1/users'):
            with self.subTest(text=text):
                self.assertFalse(is_shortcut(text))
                self.assertIsNone(parse_shortcut(text))

    def test_supported_commands_parse_explicit_arguments(self):
        self.assertEqual(parse_shortcut('/help')['name'], 'help')
        self.assertEqual(parse_shortcut('/memory')['name'], 'memory')
        self.assertEqual(parse_shortcut('/read build.gradle'), {'name':'read', 'path':'build.gradle'})
        self.assertEqual(parse_shortcut('/results reports/TEST-pilot.xml'), {'name':'results', 'path':'reports/TEST-pilot.xml'})
        self.assertEqual(parse_shortcut('/read "docs/project notes.md"')['path'], 'docs/project notes.md')

    def test_missing_unknown_extra_or_multiline_arguments_are_local_usage_errors(self):
        for text in ('/unknown', '/read', '/results', '/help extra', '/memory extra', '/read file.py\nrun tests', '/results x.xml\nconnect Jira'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_shortcut(text)

    def test_paths_cannot_escape_or_expose_credentials(self):
        for path in ('../secret.txt', r'..\secret.txt', '/outside.txt', r'C:\outside.txt', '//server/share/file.txt',
                     '.env', '.env.local', '.git/config', '.aws/credentials', '.ssh/id_rsa', 'folder/../file.txt', 'file.txt:stream',
                     '<relative-file>', 'file.txt\x00'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                parse_shortcut('/read ' + path)

    def test_results_require_supported_native_report_extension(self):
        for path in ('report.html', 'report.txt', 'runner.java'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                parse_shortcut('/results ' + path)


class LocalShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        self.scope = {'memory_user_id':'u', 'memory_namespace':'p', 'project_id':'project-' + 'a'*32,
                      'bound_project_root':str(self.project)}
        self.state = dict(self.scope, project_root=str(self.project))

    def test_help_needs_no_project_and_memory_uses_existing_graph_path(self):
        help_reply = local_shortcut_reply('/help', {})
        self.assertIn('/read', help_reply['answer'])
        self.assertIn('/results', help_reply['answer'])
        self.assertEqual(help_reply['route'], 'shortcut')
        self.assertIsNone(local_shortcut_reply('/memory', self.state))
        self.assertIsNone(local_shortcut_reply('hello', self.state))

    def test_file_read_is_bounded_and_does_not_execute_or_call_network(self):
        path = self.project / 'notes.txt'
        path.write_text('\n'.join('saved line ' + str(i) for i in range(1, 102)), encoding='utf-8')
        with patch('subprocess.run', side_effect=AssertionError('no command')), patch('requests.sessions.Session.request', side_effect=AssertionError('no provider')):
            result = local_shortcut_reply('/read notes.txt', self.state)
        self.assertIn('saved line 80', result['answer'])
        self.assertNotIn('saved line 81', result['answer'])
        self.assertIn('notes.txt', result['answer'])
        self.assertEqual(result['route'], 'shortcut')
        self.assertEqual(result['task_status'], 'completed')

    def test_local_read_uses_only_selected_project(self):
        (self.project / 'same.txt').write_text('selected-project-marker', encoding='utf-8')
        (self.root / 'same.txt').write_text('outside-project-marker', encoding='utf-8')
        result = local_shortcut_reply('/read same.txt', self.state)
        self.assertIn('selected-project-marker', result['answer'])
        self.assertNotIn('outside-project-marker', result['answer'])
        for state in ({}, {'project_root':str(self.project)}):
            with self.subTest(state=state):
                reply = local_shortcut_reply('/read same.txt', state)
                self.assertNotEqual(reply['task_status'], 'completed')
                self.assertNotIn('selected-project-marker', reply['answer'])

    def test_native_failed_results_are_observations_without_run(self):
        report = self.project / 'TEST-pilot.xml'
        report.write_text('<testsuite><testcase name="failed_case" classname="Demo"><failure>expected state absent</failure></testcase><testcase name="passed_case" classname="Demo"/></testsuite>', encoding='utf-8')
        with patch('agent.tools.project_tools.ProjectTools.run_command', side_effect=AssertionError('no run')), patch('requests.sessions.Session.request', side_effect=AssertionError('no provider')):
            result = local_shortcut_reply('/results TEST-pilot.xml', self.state)
        self.assertEqual(result['route'], 'shortcut')
        self.assertIn('failed_case', result['answer'])
        self.assertIn('failed', result['answer'].lower())
        self.assertIn('passed', result['answer'].lower())
        self.assertNotIn('all tests passed', result['answer'].lower())

    def test_unreadable_unsupported_and_invalid_commands_do_not_fall_through(self):
        (self.project / 'invalid.xml').write_text('<broken', encoding='utf-8')
        for question in ('/read missing.txt', '/results invalid.xml', '/erase all', '/read ../outside.txt'):
            with self.subTest(question=question), patch('requests.sessions.Session.request', side_effect=AssertionError('no provider')):
                result = local_shortcut_reply(question, self.state)
                self.assertIsNotNone(result)
                self.assertNotEqual(result['task_status'], 'completed')

    def test_shared_runtime_archives_one_local_read_without_graph_or_summary(self):
        (self.project / 'notes.txt').write_text('runtime evidence', encoding='utf-8')
        catalog = ChatCatalog(self.root/'chats.sqlite3', 'u', 'p')
        catalog.register('default')
        saved = {'history':'old '*4000, 'summary':'retained'}
        graph = Mock()
        graph.get_state.return_value = SimpleNamespace(values=saved)
        with patch('agent.runtime.summaries.compact_context', side_effect=AssertionError('no model summary')):
            result = run_turn(graph, {'configurable':{'thread_id':'shortcut'}}, catalog, 'default', '/read notes.txt',
                              self.root, request_scope=self.scope)
        graph.invoke.assert_not_called()
        self.assertEqual(result['persistence_status'], {'archive_saved':True, 'checkpoint_saved':True})
        rows = catalog.transcript('default')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['question'], '/read notes.txt')
        self.assertIn('runtime evidence', rows[0]['answer'])
        self.assertEqual(graph.update_state.call_args.args[1]['question'], '/read notes.txt')

    def test_memory_alias_uses_existing_graph_and_preserves_user_message(self):
        catalog = ChatCatalog(self.root/'chats.sqlite3', 'u', 'p')
        catalog.register('default')
        graph = Mock()
        graph.get_state.return_value = SimpleNamespace(values={})
        graph.invoke.return_value = {'answer':'scoped saved facts', 'route':'memory', 'task_status':'completed', 'execution_outcome':'completed'}
        result = run_turn(graph, {'configurable':{'thread_id':'memory-shortcut'}}, catalog, 'default', '/memory',
                          self.root, request_scope=self.scope)
        self.assertEqual(graph.invoke.call_args.args[0]['question'], 'SHOW MEMORY')
        self.assertEqual(graph.invoke.call_args.args[0]['project_id'], self.scope['project_id'])
        self.assertEqual(catalog.transcript('default')[0]['question'], '/memory')
        self.assertEqual(result['answer'], 'scoped saved facts')

    def test_normal_messages_keep_the_existing_graph_path(self):
        catalog = ChatCatalog(self.root/'chats.sqlite3', 'u', 'p')
        catalog.register('default')
        graph = Mock()
        graph.get_state.return_value = SimpleNamespace(values={})
        graph.invoke.return_value = {'answer':'normal answer', 'route':'direct', 'task_status':'completed'}
        run_turn(graph, {'configurable':{'thread_id':'normal-message'}}, catalog, 'default', 'hello', self.root)
        self.assertEqual(graph.invoke.call_args.args[0]['question'], 'hello')


class ShortcutProviderSelectionTests(unittest.TestCase):
    def test_shortcut_paths_bypass_natural_language_git_prehandlers(self):
        from agent.interfaces.browser import BrowserBackend
        backend = BrowserBackend.__new__(BrowserBackend)
        backend.catalog = Mock()
        backend.catalog.get.return_value = {'session':'chat'}
        backend.user, backend.space = 'u', 'p'
        backend.graph = Mock()
        backend.request_scope = lambda: None
        backend.session_config = lambda *args: {'configurable':{'thread_id':'shortcut'}}
        with patch('agent.runtime.git_workspace.git_status_reply', side_effect=AssertionError('filename is not a Git status request')), \
             patch('agent.policies.routing.git_write_mode', side_effect=AssertionError('filename is not a Git publication request')), \
             patch('agent.runtime.turns.run_turn', return_value={'answer':'saved file content', 'notices':[], 'route':'shortcut'}) as turn:
            for question in ('/read docs/git status.md', '/read docs/git push.md'):
                self.assertEqual(backend.submit('chat', question)['answer'], 'saved file content')
        self.assertEqual(turn.call_count, 2)

    def test_local_shortcut_does_not_require_provider_configuration(self):
        from agent.interfaces.browser import BrowserBackend
        backend = BrowserBackend.__new__(BrowserBackend)
        backend.provider_info = Mock(side_effect=AssertionError('no provider lookup'))
        backend.submit = Mock(return_value={'answer':'local reply'})
        self.assertEqual(backend.submit_selected('chat', '/help', 'unconfigured')['answer'], 'local reply')
        backend.submit.assert_called_once_with('chat', '/help')
        backend.provider_info.assert_not_called()

    def test_normal_message_still_requires_valid_provider_configuration(self):
        from agent.interfaces.browser import BrowserBackend
        from agent.providers.errors import ProviderError
        backend = BrowserBackend.__new__(BrowserBackend)
        backend.provider_info = Mock(return_value={'supported':False, 'model':'', 'local':False, 'key_present':False})
        backend.submit = Mock()
        with self.assertRaises(ProviderError):
            backend.submit_selected('chat', 'hello', 'unconfigured')
        backend.submit.assert_not_called()


class ShortcutBrowserTests(unittest.TestCase):
    def setUp(self):
        # Reuse setup only; do not inherit or rerun the accepted UI test suite.
        from tests.test_streamlit_ui import BrowserTests
        BrowserTests.setUp(self)

    def test_menu_prefills_help_without_creating_chat_or_submitting(self):
        self.app.run()
        active = self.app.session_state['active_chat']
        self.app.button(key='shortcut_help').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(self.app.session_state['active_chat'], active)
        self.assertTrue(self.app.session_state['chat_draft'])
        self.assertIsNone(self.backend.get_chat(active))
        self.assertEqual(self.app.chat_input[0].proto.value, '/help')

    def test_project_only_menu_items_disabled_without_selection(self):
        self.app.run()
        self.assertTrue(self.app.button(key='shortcut_read').disabled)
        self.assertTrue(self.app.button(key='shortcut_results').disabled)
        self.assertFalse(self.app.button(key='shortcut_memory').disabled)
        self.assertEqual(self.backend.calls, [])

    def test_invalid_shortcut_does_not_create_chat_or_reach_backend(self):
        self.app.run()
        active = self.app.session_state['active_chat']
        for question in ('/read', '/results', '/unsupported', '/help extra'):
            self.app.chat_input[0].set_value(question).run()
            self.assertFalse(self.app.exception)
            self.assertEqual(self.app.session_state['active_chat'], active)
            self.assertIsNone(self.backend.get_chat(active))
            self.assertEqual(self.backend.calls, [])

    def test_memory_shortcut_does_not_send_attached_document(self):
        self.app.run()
        active = self.app.session_state['active_chat']
        attachment = {'id':'fixture', 'name':'private.txt', 'text':'private attachment marker', 'truncated':False}
        self.app.session_state['attachment_collections'] = {active:[attachment]}
        self.app.chat_input[0].set_value('/memory').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.backend.calls), 1)
        self.assertEqual(self.backend.calls[0][1], '/memory')
        self.assertNotIn('private attachment marker', self.backend.calls[0][1])

    def test_normal_message_with_attachment_keeps_existing_behavior(self):
        self.app.run()
        active = self.app.session_state['active_chat']
        attachment = {'id':'fixture', 'name':'notes.txt', 'text':'normal attachment marker', 'truncated':False}
        self.app.session_state['attachment_collections'] = {active:[attachment]}
        self.app.chat_input[0].set_value('Summarize this document').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.backend.calls), 1)
        self.assertIn('normal attachment marker', self.backend.calls[0][1])


if __name__ == '__main__':
    unittest.main()
