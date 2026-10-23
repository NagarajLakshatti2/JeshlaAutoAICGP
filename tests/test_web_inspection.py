"""Browser discovery policy and approval controls; external requests are mocked."""
import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch
from agent.tools.project_tools import ProjectTools
from integrations.web import inspection


class WebInspectionTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name);self.tools=ProjectTools(str(self.root))

    def process(self,reply=None):
        worker=Mock();worker.returncode=0;worker.poll.return_value=0
        worker.communicate.return_value=(json.dumps(reply or {'status':'inspected','url':'https://example.test','fields':[],'buttons':[]}), '')
        return worker

    def test_reads_are_confined_to_selected_https_origin(self):
        for url,method in [('https://example.test/a','GET'),('https://example.test/a','HEAD')]:
            self.assertTrue(inspection.allow_request(url,method,'https://example.test/#inputs'))
        for url,method in [('https://other.test/a','GET'),('http://example.test/a','GET'),
                           ('https://example.test:444/a','GET'),('https://u:p@example.test/a','GET'),
                           ('https://example.test/a','POST'),('file:///tmp/secret','GET'),
                           ('http://127.0.0.1/','GET'),('https://example.test/a','DELETE')]:
            with self.subTest(url=url,method=method):self.assertFalse(inspection.allow_request(url,method,'https://example.test'))

    def test_private_resolved_targets_are_rejected_before_browser_launch(self):
        from agent.tools.web_pages import public_target
        for address in ('127.0.0.1','10.1.1.1','::1','169.254.169.254'):
            with self.subTest(address=address),self.assertRaises(ValueError):
                public_target('https://example.test',resolver=lambda *a:[address])

    def test_transition_addresses_cannot_hide_private_ipv4(self):
        self.assertEqual(inspection.validate_public_browser_address('64:ff9b::4b02:3c05'),'64:ff9b::4b02:3c05')
        for address in ('64:ff9b::7f00:1','64:ff9b::a00:1','2002:7f00:0001::'):
            with self.subTest(address=address),self.assertRaises(ValueError):inspection.validate_public_browser_address(address)

    def test_discovery_uses_bounded_worker_and_saved_evidence(self):
        worker=self.process()
        with patch.object(inspection.subprocess,'Popen',return_value=worker) as launch:
            result=self.tools.inspect_browser_page('https://example.test',limit=10)
        self.assertTrue((self.root/result['inspection_file']).is_file())
        self.assertEqual(result['fields'],[])
        self.assertEqual(result['inspection_sha256'],hashlib.sha256((self.root/result['inspection_file']).read_bytes()).hexdigest())
        self.assertIn('integrations.web.inspection_worker',launch.call_args.args[0])
        self.assertEqual(worker.communicate.call_args.kwargs['timeout'],inspection.TIMEOUT_SECONDS)
        worker.stdin.close.assert_called_once()

    def test_invalid_bounds_urls_and_paths_never_launch(self):
        calls=[lambda:self.tools.inspect_browser_page('file:///tmp/no'),
               lambda:self.tools.inspect_browser_page('http://example.test'),
               lambda:self.tools.inspect_browser_page('https://example.test',limit=True),
               lambda:self.tools.inspect_browser_page('https://example.test',limit=41),
               lambda:self.tools.inspect_browser_page('https://example.test',evidence_folder='../outside'),
               lambda:self.tools.inspect_browser_page('https://example.test',evidence_folder='.env.secret')]
        with patch.object(inspection.subprocess,'Popen') as launch:
            for call in calls:
                with self.assertRaises(ValueError):call()
            launch.assert_not_called()
        self.assertEqual(list(self.root.iterdir()),[])

    def test_timeout_kills_worker_and_claims_no_inspection(self):
        worker=self.process();worker.poll.return_value=None
        worker.communicate.side_effect=subprocess.TimeoutExpired('fixture',1)
        with patch.object(inspection.subprocess,'Popen',return_value=worker):
            with self.assertRaisesRegex(RuntimeError,'deadline'):self.tools.inspect_browser_page('https://example.test')
        worker.kill.assert_called_once();worker.wait.assert_called_once()

    def test_invalid_or_blocked_worker_result_never_claims_inspected(self):
        for reply in (['not an object'],{'status':'blocked','error':'No browser'},
                      {'status':'inspected','fields':'invented'}, {'status':'inspected','fields':[{}]*21}):
            worker=self.process(reply)
            with self.subTest(reply=reply),patch.object(inspection.subprocess,'Popen',return_value=worker):
                with self.assertRaises(RuntimeError):self.tools.inspect_browser_page('https://example.test')

    def test_controlled_tool_is_available_only_on_project_path(self):
        from agent.tool_policy import CONTROLLED_PROJECT_ACTIONS,READ_ONLY_PROJECT_ACTIONS
        from agent.runtime.conversation import TOOL_SPECS
        from agent.langgraph.langgraph_agent import router_node
        self.assertIn('inspect_browser_page',CONTROLLED_PROJECT_ACTIONS)
        self.assertNotIn('inspect_browser_page',READ_ONLY_PROJECT_ACTIONS)
        self.assertNotIn('inspect_browser_page',{s['function']['name'] for s in TOOL_SPECS})
        with patch('builtins.print'):
            self.assertEqual(router_node({'question':'inspect_browser_page https://example.test'})['route'],'project')


if __name__=='__main__':unittest.main()
