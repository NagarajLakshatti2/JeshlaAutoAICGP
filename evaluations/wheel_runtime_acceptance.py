"""Offline non-editable wheel acceptance; --fresh installs cached core dependencies.

Default mode reuses dependencies. --fresh uses a new isolated virtual environment.
Neither mode is a physical browser click or live-provider acceptance test.
Builds and installs into owned temporary folders; never installs into the working
venv, copies real secrets/state, downloads models or invokes hosted providers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORKER = r"""
import contextlib,io,json,os,sys
from pathlib import Path
from unittest.mock import patch

def blocked(*args,**kwargs):raise AssertionError('Wheel acceptance forbids network or browser launches')

with contextlib.ExitStack() as stack:
    stack.enter_context(patch('requests.sessions.Session.request',side_effect=blocked))
    for name in ('open','open_new','open_new_tab'):
        stack.enter_context(patch('webbrowser.'+name,side_effect=blocked))
    from agent.config.paths import APPLICATION_ROOT,DATA_ROOT
    install=Path(os.environ['WHEEL_CHECK_INSTALL']).resolve()
    expected=Path(os.environ['WHEEL_CHECK_DATA']).resolve()
    assert APPLICATION_ROOT==install,(APPLICATION_ROOT,install)
    assert DATA_ROOT==expected,(DATA_ROOT,expected)
    assert not expected.is_relative_to(install)
    import agent,rag.paths,rag.retrieval,rag.query
    from agent.interfaces import browser
    from agent.langgraph import langgraph_agent as module
    from integrations.jira import test_case_agent
    from agent.langgraph import jira_workflow_node
    assert Path(agent.__file__).resolve().is_relative_to(install)
    fresh=os.environ.get('WHEEL_FRESH')=='1'
    if fresh:
        import importlib.metadata,sysconfig
        assert sys.prefix!=sys.base_prefix
        assert 'include-system-site-packages = false' in (Path(sys.prefix)/'pyvenv.cfg').read_text(encoding='utf-8').lower()
        assert Path(sysconfig.get_path('purelib')).resolve()==install
        working=Path(os.environ['WHEEL_WORKING_VENV']).resolve()
        assert Path(sys.prefix).resolve()!=working
        assert not any(Path(value).resolve().is_relative_to(working) for value in sys.path if value)
        assert not any((Path(value)/'agent/config/paths.py').is_file() for value in sys.path if value and Path(value).resolve()!=install)
        dist=importlib.metadata.distribution('jeshla-auto-ai')
        direct=json.loads(dist.read_text('direct_url.json'))
        assert not direct.get('dir_info',{}).get('editable',False)
        assert direct['url'].endswith('.whl')
        assert Path(dist.locate_file('')).resolve()==install
    assert module.PROJECT_ROOT==browser.ROOT==test_case_agent.APP_ROOT==jira_workflow_node.APP_ROOT==expected
    assert rag.paths.RAG_DIR==rag.retrieval.DATA_DIR==rag.query.RAG_DIR==expected/'rag'
    assert rag.query.OUTPUT_DIR==expected/'outputs'
    assert module.DB_PATH==expected/'agent_memory.db'
    from agent.tools import web_pages
    assert web_pages.APPLICATION_ROOT==install
    # The installed module's actual main/console paths run without a model call.
    console=io.StringIO()
    with contextlib.redirect_stdout(console),patch.object(sys,'argv',['agent','--input-mode','end','--session','wheel-console','--user','fixture-user','--memory-space','fixture-space']),patch.object(sys,'stdin',io.StringIO('REMEMBER wheel_console = installed\nEND\nSHOW MEMORY\nEND\nEXIT\n')):
        module.main()
    assert 'Saved memory: wheel_console' in console.getvalue()
    assert 'wheel_console' in console.getvalue()
    with contextlib.redirect_stdout(io.StringIO()):
        backend=browser.BrowserBackend()
        session=backend.create_chat('Installed wheel fixture')
        result=backend.submit(session,'REMEMBER wheel_browser = installed')
        assert 'Saved memory: wheel_browser' in result['answer'],result
        assert len(backend.turns(session))==1
        facts=backend.memory_records()
        assert {'wheel_browser','wheel_console'}<={item['key'] for item in facts}
        backend.save_model_settings('ollama','fixture-wheel-model')
        assert 'OLLAMA_MODEL=fixture-wheel-model' in (expected/'.env').read_text(encoding='utf-8')
        module.graph.close()
    rendered=False
    if os.environ.get('WHEEL_CHECK_UI')=='1':
        with contextlib.redirect_stdout(io.StringIO()):
            import streamlit as st
            from streamlit.testing.v1 import AppTest
            st.cache_resource.clear()
            app=AppTest.from_file(str(install/'streamlit_app.py'),default_timeout=45).run()
            assert not app.exception and not app.error,(list(app.exception),list(app.error))
            assert len(app.chat_input)==1
            assert any(item.value=='What would you like to build?' for item in app.title)
            rendered=True
            st.cache_resource.clear()
            module.graph.close()
    assert (expected/'agent_memory.db').is_file()
    assert (expected/'outputs/memory/chats.sqlite3').is_file()
    assert (expected/'outputs/memory/long_term_memory.sqlite3').is_file()
    assert not list(Path.cwd().glob('outputs'))
    assert list(Path(os.environ['AI_PROJECT_ROOT']).iterdir())==[]
    print(json.dumps({'passed':True,'installed_package_used':True,'config_data_separate_from_code':True,'console_memory_commands':True,'browser_backend_memory_and_archive':True,'settings_editor_uses_data_root':True,'rag_and_jira_runtime_paths':True,'page_worker_keeps_code_root':True,'state_file_count':sum(p.is_file() for p in expected.rglob('*')),'network':'blocked','generated_code_executed':False,'isolated_fresh_environment':fresh,'framework_initial_render':rendered,'python':sys.version.split()[0],'streamlit':__import__('importlib.metadata',fromlist=['version']).version('streamlit')}))
"""


def digest_tree(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh',action='store_true',help='Install the wheel plus core dependencies in a new venv; never reuse runtime site-packages.')
    parser.add_argument('--wheelhouse',type=Path,help='Existing public dependency wheels; required with --fresh.')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/acceptance/ws8-wheel-runtime-20261023')
    args=parser.parse_args()
    if args.fresh and (not args.wheelhouse or not args.wheelhouse.is_dir() or not any(args.wheelhouse.glob('*.whl'))):
        parser.error('--fresh requires an existing --wheelhouse with dependency wheels')
    if args.wheelhouse and not args.fresh:parser.error('--wheelhouse requires --fresh')
    from evaluations.core_install_acceptance import copy_source,isolated_environment,fingerprint_environment
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    report={'status':'P','scope':__doc__.strip(),'fresh_environment_requested':args.fresh,'profile':'core','stages':[],'live_provider_requests':0}
    before=fingerprint_environment()
    config=ROOT/'.env';settings=hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None
    began=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='jeshla-wheel-runtime-') as directory:
        fixture=Path(directory).resolve();source=fixture/'source';source.mkdir()
        copied=copy_source(source)
        install=fixture/'installed';cwd=fixture/'unrelated';cwd.mkdir()
        (cwd/'.env').write_text('LLM_PROVIDER=wrong-cwd-canary\n',encoding='utf-8')
        inspected=fixture/'inspected';inspected.mkdir()
        env=isolated_environment(source,Path(sys.executable).parent)
        env.pop('JESHLA_HOME',None)
        env.update(PYTHONDONTWRITEBYTECODE='1',PIP_NO_INDEX='1',PYTHONPATH=str(install),AI_PROJECT_ROOT=str(inspected),
                   AI_MEMORY_USER_ID='fixture-user',AI_MEMORY_NAMESPACE='fixture-space',AI_SUMMARY_THRESHOLD_CHARS='16000')
        def stage(name,command,timeout,environment=None):
            start=time.monotonic()
            print(json.dumps({'stage':name,'status':'running'}),flush=True)
            proc=subprocess.Popen(command,cwd=cwd,env=environment or env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            timed_out=False
            try:stdout,stderr=proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out=True
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False)
                if proc.poll() is None:proc.kill()
                stdout,stderr=proc.communicate(timeout=10)
            (output/(name+'.log')).write_text(stdout+'\n'+stderr,encoding='utf-8')
            row={'name':name,'passed':not timed_out and proc.returncode==0,'seconds':round(time.monotonic()-start,2),'timed_out':timed_out,'process_stopped':proc.poll() is not None}
            report['stages'].append(row)
            print(json.dumps(row),flush=True)
            if not row['passed']:raise RuntimeError('Owned acceptance stage failed: '+name)
            return stdout
        try:
            artifacts=fixture/'dist'
            stage('build-wheel',[sys.executable,'-B','-m','build','--wheel','--no-isolation','--outdir',str(artifacts),str(source)],75)
            wheels=list(artifacts.glob('*.whl'));assert len(wheels)==1
            runtime_python=sys.executable
            if args.fresh:
                fresh=fixture/'venv'
                stage('create-fresh-venv',[sys.executable,'-m','venv',str(fresh)],45)
                scripts=fresh/('Scripts' if os.name=='nt' else 'bin')
                runtime_python=str(scripts/('python.exe' if os.name=='nt' else 'python'))
                install=(fresh/'Lib/site-packages') if os.name=='nt' else fresh/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
                env.pop('PYTHONPATH',None)
                env.update(PATH=str(scripts)+os.pathsep+env.get('PATH',''),VIRTUAL_ENV=str(fresh),
                           LOCALAPPDATA=str(fixture/'local-app-data'),XDG_DATA_HOME=str(fixture/'xdg-data'))
                cache=args.wheelhouse.resolve()
                report['wheelhouse_manifest']=[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(cache.glob('*.whl'))]
                stage('fresh-wheel-and-core-dependency-install',[runtime_python,'-B','-m','pip','install','--no-index','--find-links',str(cache),'--no-compile',str(wheels[0])],240)
                stage('fresh-pip-check',[runtime_python,'-B','-m','pip','check'],30)
                report['dependencies']='Core wheel dependencies resolved offline and installed in a new venv with system-site-packages disabled.'
            else:
                stage('install-wheel-target',[sys.executable,'-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(install),str(wheels[0])],45)
                report['dependencies']='Existing working-venv runtime dependencies; no fresh dependency resolution acceptance.'
            package_before=digest_tree(install)
            report['wheel_sha256']=hashlib.sha256(wheels[0].read_bytes()).hexdigest()
            for mode in ('default-user-data','explicit-home'):
                child_env=dict(env,LOCALAPPDATA=str(fixture/'local-app-data'),XDG_DATA_HOME=str(fixture/'xdg-data'))
                if mode=='explicit-home':
                    state=fixture/'explicit-state';child_env['JESHLA_HOME']=str(state)
                else:
                    state=(fixture/'local-app-data/JeshlaAutoAI') if os.name=='nt' else (fixture/'xdg-data/jeshlaautoai')
                state.mkdir(parents=True)
                (state/'.env').write_text('LLM_PROVIDER=groq\nGROQ_API_KEY=fixture-not-real\nGROQ_MODEL=fixture-model\n',encoding='utf-8')
                child_env.update(WHEEL_CHECK_INSTALL=str(install),WHEEL_CHECK_DATA=str(state),WHEEL_WORKING_VENV=str(Path(sys.prefix).resolve()),WHEEL_FRESH='1' if args.fresh else '0',WHEEL_CHECK_UI='1' if args.fresh and mode=='default-user-data' else '0',STREAMLIT_BROWSER_GATHER_USAGE_STATS='false')
                stage(mode+'-console-help',[runtime_python,'-B','-m','agent.langgraph.langgraph_agent','--help'],40,child_env)
                text=stage(mode+'-runtime',[runtime_python,'-B','-c',WORKER],60,child_env)
                report[mode]=json.loads(text)
                if args.fresh:stage(mode+'-installed-command-help',[str(scripts/('jeshla-auto-ai.exe' if os.name=='nt' else 'jeshla-auto-ai')),'--help'],40,child_env)
            report['installed_code_unchanged']=package_before==digest_tree(install)
            report['cwd_unchanged']=sorted(p.name for p in cwd.iterdir())==['.env']
            report['inspected_project_unchanged']=not list(inspected.iterdir())
            report['status']='Y' if all(report[k] for k in ('installed_code_unchanged','cwd_unchanged','inspected_project_unchanged')) else 'P'
        except Exception as error:
            report.update(error_type=type(error).__name__,error=str(error)[:300])
    report.update(fixture_removed=not fixture.exists(),working_packages_unchanged=before==fingerprint_environment(),
        saved_settings_unchanged=settings==(hashlib.sha256(config.read_bytes()).hexdigest() if config.exists() else None),seconds=round(time.monotonic()-began,2),source_files_copied=len(copied))
    if not all(report[k] for k in ('fixture_removed','working_packages_unchanged','saved_settings_unchanged')):report['status']='P'
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0 if report['status']=='Y' else 1


if __name__=='__main__':raise SystemExit(main())
