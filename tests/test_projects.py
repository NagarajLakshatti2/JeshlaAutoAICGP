"""Local project boundaries, legacy preservation and UI switching without providers."""
import ast
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.storage.projects import ProjectCatalog,ProjectConfigurationError,project_namespace
from agent.storage.chats import ChatCatalog
from agent.runtime.project_context import resolve_project_root
from agent.runtime.project_scope import validate_request_scope
from agent.interfaces.browser import BrowserBackend
from agent.actions.receipts import ActionBlocked


class ProjectRegistryTests(unittest.TestCase):
    def test_register_reopen_deduplicate_and_owner_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project=root/'source';project.mkdir();(project/'keep.txt').write_text('unchanged')
            store=ProjectCatalog(root/'projects.sqlite3','u','general')
            row=store.add_local(' First project ',str(project))
            self.assertEqual(store.add_local('Duplicate label',str(project))['id'],row['id'])
            self.assertEqual(ProjectCatalog(store.path,'u','general').get(row['id']),row)
            self.assertEqual(ProjectCatalog(store.path,'other','general').list(),[])
            self.assertEqual(ProjectCatalog(store.path,'u','other').list(),[])
            self.assertIsNone(ProjectCatalog(store.path,'other','general').get(row['id']))
            self.assertEqual((project/'keep.txt').read_text(),'unchanged')
            self.assertEqual(list(project.iterdir()),[project/'keep.txt'])

    def test_invalid_name_or_path_does_not_register(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ProjectCatalog(Path(folder)/'projects.sqlite3','u','general')
            for name,path in [('',folder),('x'*101,folder),('Name','relative'),('Name',str(Path(folder)/'missing')),('Name','')]:
                with self.assertRaises(ProjectConfigurationError):store.add_local(name,path)
            self.assertEqual(store.list(),[])

    def test_scope_is_stable_unique_and_does_not_override_bound_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=root/'a';a.mkdir();b=root/'b';b.mkdir()
            project=ProjectCatalog(root/'p.sqlite3','u','general').add_local('A',str(a))
            scope={'memory_user_id':'u','memory_namespace':project_namespace('general',project['id']),'project_id':project['id'],'bound_project_root':str(a.resolve())}
            state=validate_request_scope(scope)
            self.assertEqual(resolve_project_root({**state,'question':'Explain this project'},b),str(a.resolve()))
            self.assertEqual(resolve_project_root({**state,'question':'My project root is '+str(a)},b),str(a.resolve()))
            with self.assertRaises(ProjectConfigurationError):resolve_project_root({**state,'question':'My project root is '+str(b)},b)
            self.assertNotEqual(project_namespace('other',project['id']),scope['memory_namespace'])
            a.rmdir()
            with self.assertRaises(ProjectConfigurationError):validate_request_scope(scope)


class ProjectBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.a=self.root/'source-a';self.a.mkdir();self.b=self.root/'source-b';self.b.mkdir()
        (self.a/'identity.txt').write_text('project A');(self.b/'identity.txt').write_text('project B')
        self.patch=patch('agent.interfaces.browser.ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        self.summary=patch('agent.runtime.summaries.summary_due',return_value=False);self.summary.start();self.addCleanup(self.summary.stop)
        self.base=BrowserBackend.__new__(BrowserBackend);self.base.user='u';self.base.space='general';self.base.provider='groq'
        self.base.catalog=ChatCatalog(self.root/'outputs/memory/chats.sqlite3','u','general');self.base.catalog.register('default')
        self.base.provider_info=lambda provider=None:{'provider':provider or 'groq','model':'fixture-model','key_present':True,'local':False,'supported':True}
        self.base.session_config=lambda session,user,space:{'configurable':{'thread_id':json.dumps([user,space,session])}}
        source=(Path(__file__).resolve().parents[1]/'agent/langgraph/langgraph_agent.py').read_text(encoding='utf-8')
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in {'load_long_term_memory_node','memory_command_node','show_memory_node'}]
        functions={'PROJECT_ROOT':self.root,'AgentState':dict,'os':os,'json':json,'re':re}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'isolated-project-memory','exec'),functions)
        self.functions=functions;self.states={};self.invocations=[]
        def get(config):return SimpleNamespace(values=dict(self.states.get(config['configurable']['thread_id'],{})))
        def update(config,values):self.states.setdefault(config['configurable']['thread_id'],{}).update(values)
        def invoke(state,config):
            self.invocations.append(dict(state));loaded=functions['load_long_term_memory_node'](state)
            state={**state,**loaded}
            if state['question'].startswith(('REMEMBER','FORGET')):result=functions['memory_command_node'](state)
            elif state['question']=='SHOW MEMORY':result=functions['show_memory_node'](state)
            else:result={'answer':'Project answer for '+state.get('project_id','General')}
            result={**state,**result,'route':'memory','task_status':'completed','execution_outcome':'completed'};update(config,result);return result
        self.base.graph=SimpleNamespace(get_state=get,update_state=update,invoke=invoke)
        self.pa=self.base.add_project('Project A',str(self.a));self.pb=self.base.add_project('Project B',str(self.b))
        self.view_a=self.base.for_project(self.pa['id']);self.view_b=self.base.for_project(self.pb['id'])

    def test_legacy_general_and_two_project_chats_remain_separate_after_reopen(self):
        self.base.catalog.append('default','Legacy question','Legacy answer')
        ca=self.view_a.create_chat('A chat');cb=self.view_b.create_chat('B chat')
        self.view_a.submit(ca,'REMEMBER report_name = Alpha')
        self.view_b.submit(cb,'REMEMBER report_name = Beta')
        self.assertIn('Alpha',self.view_a.submit(ca,'SHOW MEMORY')['answer'])
        self.assertNotIn('Beta',self.view_a.submit(ca,'SHOW MEMORY')['answer'])
        self.assertIn('Beta',self.view_b.submit(cb,'SHOW MEMORY')['answer'])
        self.assertEqual(self.base.turns('default')[0]['answer'],'Legacy answer')
        self.assertEqual(self.base.list_chats()[0]['session'],'default')
        self.assertEqual([r['session'] for r in self.view_a.list_chats()],[ca])
        self.assertEqual(self.view_b.turns(ca),[])
        reopened=self.base.for_project(self.pa['id']);self.assertEqual(reopened.turns(ca),self.view_a.turns(ca))
        self.assertNotIn('Beta',str(self.view_a.search_chats('Beta')))
        a_states=[s for s in self.invocations if s.get('project_id')==self.pa['id']]
        self.assertTrue(all('Beta' not in str(s) for s in a_states))
        self.assertEqual(self.base.space,'general')
        general=self.view_a.for_project('');self.assertEqual(general.space,'general')
        self.assertEqual(general.turns('default')[0]['answer'],'Legacy answer')
        self.assertIsNone(general.project)

    def test_new_project_does_not_import_general_seed_facts(self):
        seed=self.root/'agent/memory/long_term_memory.json';seed.parent.mkdir(parents=True);seed.write_text('[{"text":"General seed identity"}]')
        ca=self.view_a.create_chat('A chat');answer=self.view_a.submit(ca,'SHOW MEMORY')['answer']
        self.assertNotIn('General seed identity',answer)
        self.assertEqual(self.view_a.memory_records(),[])

    def test_bound_request_scope_reaches_graph_without_process_environment_changes(self):
        ca=self.view_a.create_chat('A chat')
        before={key:os.environ.get(key) for key in ('AI_MEMORY_USER_ID','AI_MEMORY_NAMESPACE','AI_PROJECT_ROOT')}
        self.view_a.submit(ca,'Explain this project')
        current=self.invocations[-1]
        self.assertEqual(current['project_id'],self.pa['id']);self.assertEqual(current['project_root'],str(self.a.resolve()))
        self.assertEqual(current['memory_namespace'],self.view_a.space)
        self.assertEqual(before,{key:os.environ.get(key) for key in before})
        with self.assertRaises(ValueError):self.view_b.submit(ca,'Use A chat')

    def test_actions_and_downloads_are_project_bound(self):
        ca=self.view_a.create_chat('A');cb=self.view_b.create_chat('B')
        proposal={'project_root':str(self.a),'action':'create_file','arguments':{'relative_path':'approved.txt','content':'A only'}}
        token=self.view_a.actions().propose('u',self.view_a.space,ca,'create_file',proposal)
        self.assertEqual(self.view_b.pending_actions(cb),[])
        with self.assertRaises(ActionBlocked):self.view_b.decide_action(cb,token,True)
        first=self.view_a.decide_action(ca,token,True);again=self.view_a.decide_action(ca,token,True)
        self.assertEqual(first['answer'],again['answer']);self.assertEqual((self.a/'approved.txt').read_text(),'A only')
        self.assertFalse((self.b/'approved.txt').exists());self.assertEqual(self.view_b.generated_files(cb),[])
        proposal['project_root']=str(self.b);proposal['arguments']['relative_path']='wrong.txt'
        wrong=self.view_a.actions().propose('u',self.view_a.space,ca,'create_file',proposal)
        with self.assertRaises(ActionBlocked):self.view_a.decide_action(ca,wrong,True)
        self.assertFalse((self.b/'wrong.txt').exists())

    def test_actual_graph_preserves_project_memory_checkpoints_and_blocks_unconfigured_jira(self):
        from langgraph.checkpoint.sqlite import SqliteSaver
        from agent.langgraph import langgraph_agent as module
        ca=self.view_a.create_chat('Real graph A');cb=self.view_b.create_chat('Real graph B')
        with SqliteSaver.from_conn_string(str(self.root/'graph.sqlite3')) as saver,patch.object(module,'PROJECT_ROOT',self.root),patch('agent.tool_llm.call_tool_messages',side_effect=AssertionError('no model request')) as model,redirect_stdout(io.StringIO()):
            graph=module.build_graph(saver);self.view_a.graph=graph;self.view_b.graph=graph
            self.view_a.submit(ca,'REMEMBER graph_fact = Alpha-only')
            self.view_b.submit(cb,'REMEMBER graph_fact = Beta-only')
            answer=self.view_a.submit(ca,'SHOW MEMORY')['answer']
            self.assertIn('Alpha-only',answer);self.assertNotIn('Beta-only',answer)
            astate=graph.get_state(self.view_a.session_config(ca,'u',self.view_a.space)).values
            bstate=graph.get_state(self.view_b.session_config(cb,'u',self.view_b.space)).values
            self.assertEqual(astate['project_id'],self.pa['id']);self.assertEqual(bstate['project_id'],self.pb['id'])
            self.assertNotIn('Beta-only',astate['history'])
            jira=self.view_a.submit(ca,'Create Jira test cases for this project')
            self.assertEqual(jira['task_status'],'awaiting_input');self.assertIn('not configured',jira['answer'])
            model.assert_not_called()

    def test_scoped_report_tool_rejects_other_project_agent_evidence(self):
        from agent.runtime.project_scope import tools_for_state
        state=validate_request_scope(self.view_a.request_scope())
        tools=tools_for_state(state,self.root)
        self.assertEqual(tools.read_file('identity.txt')['content'].strip(),'1: project A')
        with self.assertRaises(ProjectConfigurationError):tools.build_test_report('manifest.json',str(self.root/'outputs/acceptance/projects'/self.pb['id']))


class ProjectUITests(unittest.TestCase):
    def setUp(self):
        ProjectBackendTests.setUp(self)
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        st.cache_resource.clear();self.addCleanup(st.cache_resource.clear)
        maker=patch('agent.browser_backend.make_browser_backend',return_value=self.base);maker.start();self.addCleanup(maker.stop)
        log=patch('agent.browser_activity.log_browser_event');log.start();self.addCleanup(log.stop)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'),default_timeout=30)

    def open_projects(self):
        self.app.button(key="projects_menu").click().run()
        self.assertFalse(self.app.exception)

    def test_switch_restores_project_chat_and_resets_memory_dialog_data(self):
        self.app.run();self.assertFalse(self.app.exception)
        self.open_projects()
        self.app.button(key='choose_project_'+self.pa['id']).click().run()
        self.app.chat_input[0].set_value('First A conversation').run();ca=self.app.session_state['active_chat']
        self.app.session_state['saved_facts']=[{'key':'secret','value':'A'}]
        self.open_projects()
        self.app.button(key='choose_project_'+self.pb['id']).click().run()
        self.assertFalse(self.app.exception);self.assertNotIn('saved_facts',self.app.session_state)
        self.assertNotEqual(self.app.session_state['active_chat'],ca)
        self.app.chat_input[0].set_value('First B conversation').run();cb=self.app.session_state['active_chat']
        self.assertNotEqual(ca,cb)
        self.open_projects()
        self.app.button(key='choose_project_'+self.pa['id']).click().run()
        self.assertFalse(self.app.exception);self.assertFalse(self.app.session_state['chat_opened'])
        self.app.button(key='open_chat_'+ca).click().run()
        self.assertEqual(self.app.session_state['active_chat'],ca)
        self.assertTrue(any('First A conversation'==r.value for r in self.app.markdown))
        self.assertFalse(any('First B conversation'==r.value for r in self.app.markdown))
        self.open_projects()
        self.app.button(key='clear_project_selection').click().run();self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state['chat_opened'])

    def test_add_project_form_registers_without_touching_source(self):
        c=self.root/'source-c';c.mkdir();(c/'keep.txt').write_text('keep')
        self.app.run();self.open_projects();self.app.button(key='add_project_menu').click().run();self.app.text_input(key='new_project_name').set_value('Project C')
        self.app.text_input(key='new_project_folder').set_value(str(c))
        self.app.button(key='save_local_project').click().run()
        self.assertFalse(self.app.exception)
        selected=self.app.session_state['selected_project_id']
        self.assertEqual(self.base.project_store().get(selected)['name'],'Project C')
        self.assertEqual((c/'keep.txt').read_text(),'keep');self.assertEqual(list(c.iterdir()),[c/'keep.txt'])
