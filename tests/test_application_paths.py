import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.config.paths import APPLICATION_ROOT
from agent.project_context import resolve_project_root

class ApplicationPathTests(unittest.TestCase):
    def test_user_project_boundary_does_not_redirect_application_state(self):
        original=APPLICATION_ROOT
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"AI_PROJECT_ROOT":folder}):
            self.assertEqual(resolve_project_root({},original),str(Path(folder).resolve()))
            from agent.config.paths import APPLICATION_ROOT as current
            self.assertEqual(current,original)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_anchor_import_ignores_cwd_and_has_no_file_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            env=dict(os.environ);env['PYTHONPATH']=str(APPLICATION_ROOT)
            run=subprocess.run([sys.executable,'-B','-c','import json; from agent.config.paths import APPLICATION_ROOT; print(json.dumps(str(APPLICATION_ROOT)))'],cwd=folder,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(Path(json.loads(run.stdout)),APPLICATION_ROOT)
            self.assertEqual(list(Path(folder).iterdir()),[])


class RuntimeDataPathTests(unittest.TestCase):
    def test_checkout_keeps_existing_root_and_does_not_create_folders(self):
        from agent.config.paths import resolve_data_root
        self.assertEqual(resolve_data_root(APPLICATION_ROOT,environ={}),APPLICATION_ROOT)

    def test_absolute_home_override_wins_without_using_inspected_project(self):
        from agent.config.paths import resolve_data_root
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);home=root/"runtime";inspected=root/"inspected"
            result=resolve_data_root(APPLICATION_ROOT,environ={"JESHLA_HOME":str(home),"AI_PROJECT_ROOT":str(inspected)})
            self.assertEqual(result,home.resolve())
            self.assertFalse(home.exists());self.assertFalse(inspected.exists())

    def test_relative_home_override_fails_instead_of_following_cwd(self):
        from agent.config.paths import resolve_data_root
        with self.assertRaisesRegex(ValueError,"absolute"):
            resolve_data_root(APPLICATION_ROOT,environ={"JESHLA_HOME":"relative-state"})

    def test_wheel_default_uses_local_app_data_on_windows(self):
        from agent.config.paths import resolve_data_root
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);installed=root/"site-packages";local=root/"user-local"
            result=resolve_data_root(installed,environ={"LOCALAPPDATA":str(local),"AI_PROJECT_ROOT":str(root/"inspected")},platform="nt",user_home=root/"home")
            self.assertEqual(result,(local/"JeshlaAutoAI").resolve())
            self.assertFalse(result.exists());self.assertFalse(installed.exists())

    def test_wheel_default_uses_xdg_or_home_without_writing(self):
        from agent.config.paths import resolve_data_root
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);installed=root/"site-packages";home=root/"home"
            for values,expected in (({},home/".local/share/jeshlaautoai"),({"XDG_DATA_HOME":str(root/"xdg")},root/"xdg/jeshlaautoai")):
                self.assertEqual(resolve_data_root(installed,environ=values,platform="posix",user_home=home),expected.resolve())
                self.assertFalse(expected.exists())
            self.assertEqual(resolve_data_root(installed,environ={},platform="nt",user_home=home),(home/"AppData/Local/JeshlaAutoAI").resolve())

    def test_relative_os_data_directory_is_rejected(self):
        from agent.config.paths import resolve_data_root
        for platform,variable in (("nt","LOCALAPPDATA"),("posix","XDG_DATA_HOME")):
            with self.assertRaisesRegex(ValueError,variable):
                resolve_data_root(Path(tempfile.gettempdir())/"missing-site-packages",environ={variable:"relative"},platform=platform)

    def test_override_import_keeps_code_and_data_separate_without_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);state=base/"state";cwd=base/"cwd";cwd.mkdir()
            env=dict(os.environ,PYTHONPATH=str(APPLICATION_ROOT),JESHLA_HOME=str(state),PYTHONDONTWRITEBYTECODE="1")
            code="import json; from agent.config.paths import APPLICATION_ROOT,DATA_ROOT; print(json.dumps([str(APPLICATION_ROOT),str(DATA_ROOT)]))"
            run=subprocess.run([sys.executable,"-B","-c",code],cwd=cwd,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            source,data=map(Path,json.loads(run.stdout))
            self.assertEqual(source,APPLICATION_ROOT);self.assertEqual(data,state.resolve())
            self.assertFalse(state.exists());self.assertEqual(list(cwd.iterdir()),[])

    def test_provider_config_comes_from_data_root_not_current_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);state=base/"state";state.mkdir();cwd=base/"cwd";cwd.mkdir()
            (state/".env").write_text("LLM_PROVIDER=groq\nGROQ_MODEL=fixture-data-model\n",encoding="utf-8")
            (cwd/".env").write_text("LLM_PROVIDER=gemini\nGROQ_MODEL=wrong-cwd-model\n",encoding="utf-8")
            env={k:v for k,v in os.environ.items() if k not in {"LLM_PROVIDER","GROQ_MODEL"} and not k.endswith("_API_KEY")}
            env.update(PYTHONPATH=str(APPLICATION_ROOT),JESHLA_HOME=str(state),PYTHONDONTWRITEBYTECODE="1")
            code="import os; from agent.providers.text import LLM_PROVIDER; assert LLM_PROVIDER=='groq'; assert os.getenv('GROQ_MODEL')=='fixture-data-model'; print('ok')"
            run=subprocess.run([sys.executable,"-B","-c",code],cwd=cwd,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual({p.name for p in state.iterdir()},{".env"})
            self.assertEqual({p.name for p in cwd.iterdir()},{".env"})


class InstallFixtureIsolationTests(unittest.TestCase):
    def test_rehearsal_does_not_inherit_user_runtime_home(self):
        from evaluations.core_install_acceptance import isolated_environment
        with patch.dict(os.environ,{"JESHLA_HOME":"private-user-runtime-canary"}):
            environment=isolated_environment(APPLICATION_ROOT,Path(sys.executable).parent)
        self.assertNotIn("JESHLA_HOME",environment)
        self.assertNotIn("private-user-runtime-canary",environment.values())
