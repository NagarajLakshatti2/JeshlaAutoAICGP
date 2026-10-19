"""Run isolated browser UI acceptance with installed engines and synthetic data."""
import json,os,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE=Path("C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
OUT=ROOT/("outputs/acceptance/header-busy-browser" if os.getenv("UI_HEADER_BUSY_CHECK") else ("outputs/acceptance/ui-redesign-browser" if os.getenv("UI_REDESIGN_CHECK") else ("outputs/acceptance/ui-settings-downloads-browser" if os.getenv("UI_SETTINGS_CHECK") else "outputs/acceptance/ui-enhanced-browser")))
OUT.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary)
    entry=folder/"fixture.py"
    entry.write_text("""import sys,re,os
from pathlib import Path
sys.path.insert(0,ROOT_VALUE)
import streamlit as st
from tests.test_streamlit_ui import FakeBackend
from agent.interfaces.browser import BrowserBackend
from agent.memory.long_term_memory import LongTermMemory
from agent import browser_backend,browser_activity
class FixtureBackend(FakeBackend):
    provider='groq'
    def provider_info(self,provider=None):
        provider=provider or self.provider
        return {'provider':provider,'model':'fixture-'+provider,'key_present':None if provider=='ollama' else True,'local':provider=='ollama','supported':True}
    edit_memory=BrowserBackend.edit_memory
    generated_files=BrowserBackend.generated_files
    generated_file=BrowserBackend.generated_file
    def __init__(self,folder):
        super().__init__(folder)
        from agent.actions.browser import BrowserActions
        self.user='u';self.space='p';self.store=BrowserActions(Path(folder)/'actions.sqlite3')
        token=self.store.propose('u','p','default','create_file',{'project_root':str(Path(folder).resolve()),'action':'create_file','arguments':{'relative_path':'approved-export.txt','content':'Approved fixture export'}})
        self.store.execute('u','p','default',token)
    def actions(self):return self.store
    def save_model_settings(self,provider,model):
        from agent.config.ui_settings import save_model_settings
        return save_model_settings(Path(FOLDER_VALUE)/'.env',provider,model)
    def memory_records(self):
        with LongTermMemory(Path(FOLDER_VALUE)/'facts.sqlite3') as store:return store.list('fixture','ui')
    def submit(self,session,question):
        if os.getenv("UI_HEADER_BUSY_CHECK"):
            import time
            time.sleep(6)
        match=re.fullmatch(r'REMEMBER ([A-Za-z0-9_.-]+) = (.+)',question,re.S)
        if match:
            with LongTermMemory(Path(FOLDER_VALUE)/'facts.sqlite3') as store:store.save('fixture','ui',match[1],match[2],source_kind='user_statement')
            answer='Saved memory: '+match[1]+'.'
        else:answer='Fixture answer from supplied evidence.' if os.getenv('UI_REDESIGN_CHECK') else 'Fixture response: '+question
        self.catalog.append(session,question,answer)
        return {'answer':answer,'task_status':'completed','notices':[]}
@st.cache_resource
def fixture():
    backend=FixtureBackend(FOLDER_VALUE)
    with LongTermMemory(Path(FOLDER_VALUE)/'facts.sqlite3') as store:store.save('fixture','ui','long_reference','https://example.test/'+('longpath'*100))
    if os.getenv('UI_REDESIGN_CHECK'):backend.catalog.append('default','Earlier chat question','Existing saved answer')
    return backend
browser_backend.make_browser_backend=fixture
browser_activity.log_browser_event=lambda *a,**k:None
exec(compile(Path(ROOT_VALUE,'streamlit_app.py').read_text(encoding='utf-8'),str(Path(ROOT_VALUE,'streamlit_app.py')),'exec'))
if os.getenv('UI_HEADER_BUSY_CHECK'):
    st.session_state.fixture_render_count=st.session_state.get('fixture_render_count',0)+1
    st.html('<span data-fixture-renders="'+str(st.session_state.fixture_render_count)+'" hidden></span>')
""".replace('ROOT_VALUE',repr(str(ROOT))).replace('FOLDER_VALUE',repr(str(folder))),encoding='utf-8')
    with socket.socket() as connection:
        connection.bind(('127.0.0.1',0));port=connection.getsockname()[1]
    url=f'http://127.0.0.1:{port}/JeshlaAutoAI/'
    with (OUT/'server.log').open('w',encoding='utf-8') as log:
        command=[sys.executable,'-m','streamlit','run',str(entry),'--server.address','127.0.0.1','--server.port',str(port),'--server.baseUrlPath','JeshlaAutoAI','--server.headless','true']
        if not os.getenv('UI_HEADER_BUSY_CHECK'):command+=['--server.fileWatcherType','none']
        server=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        (OUT/'fixture-process.json').write_text(json.dumps({'server_pid':server.pid,'port':port,'entry':str(entry),'status':'running'}),encoding='utf-8')
        try:
            for attempt in range(60):
                if server.poll() is not None:raise RuntimeError('Fixture server exited; inspect server.log')
                try:
                    with urllib.request.urlopen(url+'_stcore/health',timeout=1) as response:
                        if response.status==200:break
                except Exception:time.sleep(.25)
            else:raise RuntimeError('Fixture server did not become ready')
            result=subprocess.run([str(NODE),str(ROOT/('evaluations/header_busy_browser.cjs' if os.getenv('UI_HEADER_BUSY_CHECK') else ('evaluations/ui_redesign_browser.cjs' if os.getenv('UI_REDESIGN_CHECK') else 'evaluations/ui_enhanced_browser.cjs'))),url,str(OUT)],cwd=ROOT,timeout=300,env=dict(os.environ,UI_FIXTURE_ENTRY=str(entry)))
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()
            (OUT/'fixture-process.json').write_text(json.dumps({'server_pid':server.pid,'port':port,'status':'stopped'}),encoding='utf-8')
    raise SystemExit(result.returncode)
