"""Saved report filenames and prohibited Jira mentions do not start Jira routes."""
from pathlib import Path
import unittest
from unittest.mock import patch
from agent.langgraph import langgraph_agent as agent


class SavedReportRoutingTests(unittest.TestCase):
    def route(self, question):
        with patch('builtins.print'):
            return agent.router_node({'question':question})['route']

    def test_exact_authorized_packet_prompt_routes_to_project(self):
        prompt='My project root is D:\\sample.\nRead only login-review.md, lines 1–48. Explain QPH-012. Do not read other files, run commands/tests, edit files, reopen the website, connect to Jira/Git, or weaken the assertion.'
        self.assertEqual(self.route(prompt),'project')

    def test_bare_or_quoted_markdown_text_and_json_reads_route_to_project(self):
        for name in ('login-review.md','notes.markdown','results.json','run.log.txt','"report with spaces.md"'):
            with self.subTest(name=name):
                self.assertEqual(self.route('Read '+name+' and explain QPH-012. Do not connect to Jira/Git.'),'project')

    def test_existing_source_and_native_report_routes_stay_project(self):
        for name in ('build.gradle','InputTest.java','results.xml','Login.feature','main.py'):
            with self.subTest(name=name):self.assertEqual(self.route('Read '+name+'; do not connect to Jira.'),'project')

    def test_negated_jira_reference_with_test_key_is_not_external_intent(self):
        for text in ('Explain QPH-012 from the supplied evidence. Do not connect to Jira/Git.',
                     'Explain QPH-012. Never authenticate Jira.',
                     'Explain TEST-7 without contacting Jira.'):
            with self.subTest(text=text):self.assertNotIn(self.route(text),('jira','jira_workflow'))

    def test_real_positive_jira_requests_keep_their_routes(self):
        self.assertEqual(self.route('Read Jira issue TEST-7'),'jira')
        self.assertEqual(self.route('Read TEST-7 and propose Gherkin test-case subtasks'),'jira_workflow')
        self.assertEqual(self.route('Do not edit files. Read Jira TEST-7'),'jira')

    def test_ordinary_chat_and_memory_commands_remain_local(self):
        self.assertEqual(self.route('Hi'),'direct')
        self.assertEqual(self.route('SHOW MEMORY'),'memory')


if __name__=='__main__':unittest.main()
