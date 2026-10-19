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
