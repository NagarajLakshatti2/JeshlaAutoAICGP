"""Opt-in exact-commit GitHub clone and fresh cached-core install acceptance.

Clones a public HTTPS GitHub repository into an owned disposable folder, checks
the exact requested commit, and installs it directly (editable) in a new venv.
Only Git clone uses the network. Runtime probes block external/provider calls.
No working settings, data, packages, Git state or repository visibility changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROVENANCE = r"""
import sys,sysconfig,json,importlib.metadata
from pathlib import Path
source,working=map(lambda value:Path(value).resolve(),sys.argv[1:])
assert sys.prefix!=sys.base_prefix
assert Path(sys.prefix).resolve()!=working
assert 'include-system-site-packages = false' in (Path(sys.prefix)/'pyvenv.cfg').read_text().lower()
assert not any(Path(value).resolve().is_relative_to(working) for value in sys.path if value)
import agent
assert Path(agent.__file__).resolve().is_relative_to(source)
purelib=Path(sysconfig.get_path('purelib')).resolve()
dist=next(d for d in importlib.metadata.distributions(path=[str(purelib)]) if d.metadata['Name'].lower().replace('_','-')=='jeshla-auto-ai')
direct=json.loads(dist.read_text('direct_url.json'))
assert direct['dir_info']['editable'] is True
assert direct['url'].rstrip('/').casefold()==source.as_uri().rstrip('/').casefold()
print(json.dumps({'fresh_dependency_environment':True,'source_is_exact_clone':True,'editable_install_metadata_verified':True,'working_venv_excluded':True}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--defer-native-launcher',action='store_true',help='Leave the native executable gate pending while completing Python-module console/browser acceptance.')
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    url = urlsplit(args.repository)
    if url.scheme != 'https' or url.hostname != 'github.com' or url.username or url.password or url.query or url.fragment or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',url.path):
        parser.error('Use a public credential-free HTTPS github.com owner/repository URL.')
    if not re.fullmatch(r'[0-9a-fA-F]{40}',args.commit):parser.error('Provide the exact 40-character commit SHA.')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+',args.branch) or args.branch.startswith('-'):parser.error('Invalid branch name.')
    cache = args.wheelhouse.resolve()
    if not cache.is_dir() or not any(cache.glob('*.whl')):parser.error('Provide the existing dependency wheel cache.')
    output = args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    from evaluations.core_install_acceptance import isolated_environment,fingerprint_environment
    packages_before = fingerprint_environment()
    settings = ROOT/'.env'
    settings_before = hashlib.sha256(settings.read_bytes()).hexdigest() if settings.exists() else None
    report = {'status':'P','repository':args.repository,'expected_commit':args.commit.lower(),'profile':'core','dependency_source':'existing local wheel cache; package index disabled','stages':[],
              'scope':'Exact remote Git commit, direct fresh editable core install, entry points, console save/show/checkpoint reopen and Streamlit initial rendering. Not all optional profiles, live models, physical browser clicks, privacy/history resolution or full release acceptance.'}
    began = time.monotonic();deadline=began+480
    with tempfile.TemporaryDirectory(prefix='jeshla-github-clone-') as directory:
        fixture=Path(directory).resolve();clone=fixture/'repository';venv=fixture/'venv';scripts=venv/('Scripts' if os.name=='nt' else 'bin');python=scripts/('python.exe' if os.name=='nt' else 'python')
        state=fixture/'state';state.mkdir()
        env=isolated_environment(clone,scripts)
        env.update(PIP_NO_INDEX='1',PIP_FIND_LINKS=str(cache),PYTHONDONTWRITEBYTECODE='1',JESHLA_HOME=str(state),AI_DEPLOYMENT_MODE='hosted',LLM_ALLOW_LOCAL_OLLAMA='false',LLM_FALLBACK_ENABLED='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1')
        def stage(name,command,cap,cwd=fixture):
            limit=min(cap,deadline-time.monotonic())
            if limit<=0:raise TimeoutError('Overall acceptance budget exhausted.')
            row={'name':name,'status':'running'};report['stages'].append(row)
            print(json.dumps(row),flush=True)
            (output/'progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            start=time.monotonic()
            with (output/(name+'.log')).open('w',encoding='utf-8') as log:
                try:
                    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
                except OSError as error:
                    row.update(status='P',error_type=type(error).__name__,winerror=getattr(error,'winerror',None),elapsed_seconds=round(time.monotonic()-start,2))
                    log.write(str(error)+'\n')
                    raise
                try:
                    code=process.wait(timeout=limit);row['timed_out']=False
                except subprocess.TimeoutExpired:
                    row['timed_out']=True
                    # Every PID is this evaluator's owned child. No user server,
                    # browser or unrelated process is enumerated or stopped.
                    if os.name=='nt':
                        try:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT,timeout=10,check=False)
                        except subprocess.TimeoutExpired:pass
                    if process.poll() is None:process.kill()
                    process.wait(timeout=10);code=process.returncode
                row.update(status='Y' if code==0 and not row['timed_out'] else 'P',seconds=round(time.monotonic()-start,2),exit_code=code,owned_process_stopped=process.poll() is not None)
            (output/'progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(row),flush=True)
            if row['status']!='Y':raise RuntimeError('Acceptance stage failed: '+name)
            return (output/(name+'.log')).read_text(encoding='utf-8')
        try:
            stage('clone-exact-main',['git','clone','--depth','1','--single-branch','--branch',args.branch,'--',args.repository,str(clone)],90)
            actual=stage('verify-commit',['git','-C',str(clone),'rev-parse','HEAD'],10).strip().lower()
            report['actual_commit']=actual
            if actual!=args.commit.lower():raise ValueError('Remote branch moved; exact requested commit was not tested.')
            report['exact_remote_commit_verified']=True
            if (clone/'.env').exists():raise ValueError('Remote clone contains .env; private-configuration handling needs review.')
            stage('create-fresh-venv',[sys.executable,'-m','venv',str(venv)],45)
            stage('install-clone-core',[str(python),'-m','pip','install','--no-index','--find-links',str(cache),'--no-compile','-e',str(clone)],180)
            stage('check-dependencies',[str(python),'-m','pip','check'],20)
            stage('verify-install-provenance',[str(python),'-B','-c',PROVENANCE,str(clone),str(Path(sys.prefix).resolve())],20,clone)
            stage('legacy-console-help',[str(python),'-B','-m','agent.langgraph.langgraph_agent','--help'],45,clone)
            if args.defer_native_launcher:
                report['stages'].append({'name':'installed-console-help','status':'P','executed':False,'reason':'Explicitly deferred native launcher; no alternate invocation of the executable attempted.'})
            else:
                stage('installed-console-help',[str(scripts/('jeshla-auto-ai.exe' if os.name=='nt' else 'jeshla-auto-ai')),'--help'],45,clone)
            for interface in ('console','browser'):
                stage(interface+'-startup',[str(python),'-B','-m','evaluations.ci_smoke','--interface',interface,'--source',str(clone),'--output-dir',str(output/'startup')],140,clone)
                saved=json.loads((output/'startup'/(interface+'.json')).read_text(encoding='utf-8'))
                if saved['status']!='Y':raise RuntimeError('Startup acceptance returned pending.')
            stage('tracked-source-unchanged',['git','-C',str(clone),'diff','--exit-code','HEAD','--'],10)
            report['documented_python_module_and_browser_route']='Y'
            report['status']='P' if args.defer_native_launcher else 'Y'
        except Exception as error:
            report.update(error_type=type(error).__name__,last_stage=report['stages'][-1]['name'] if report['stages'] else None)
    report.update(fixture_removed=not fixture.exists(),working_packages_unchanged=packages_before==fingerprint_environment(),working_settings_unchanged=settings_before==(hashlib.sha256(settings.read_bytes()).hexdigest() if settings.exists() else None),elapsed_seconds=round(time.monotonic()-began,2),working_private_settings_copied=False,working_user_stores_copied=False,provider_requests=0,model_downloads=False)
    if not all(report[key] for key in ('fixture_removed','working_packages_unchanged','working_settings_unchanged')):report['status']='P'
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    return 0 if report['status']=='Y' else 1


if __name__=='__main__':
    raise SystemExit(main())
