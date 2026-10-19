import io,json,tempfile,unittest
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path
from unittest.mock import patch
from tests.offline_log import ProgressResult,writer
from agent.runtime.execution_log import log_execution
from agent.timing import timer

class ExecutionLoggingTests(unittest.TestCase):
    def test_stage_logs_match_and_hide_arbitrary_labels_and_error_text(self):
        with tempfile.TemporaryDirectory() as folder,patch('agent.runtime.execution_log.APPLICATION_ROOT',Path(folder)),redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                with timer('secret prompt label'):raise RuntimeError('private error body')
            files=list((Path(folder)/'outputs/logs').glob('execution-*.jsonl'))
            text=files[0].read_text();rows=[json.loads(line) for line in text.splitlines()]
            self.assertEqual(len(rows),2);self.assertEqual(rows[0]['span'],rows[1]['span'])
            self.assertEqual(rows[1]['status'],'FAILED / INTERRUPTED')
            self.assertNotIn('secret',text);self.assertNotIn('private',text)

    def test_failed_log_write_does_not_break_execution(self):
        with patch('agent.runtime.execution_log.Path.mkdir',side_effect=OSError('private failure')):
            self.assertFalse(log_execution('stage_started','LLM request',span='fixture'))

    def test_progress_records_failure_and_subtest_without_assertion_content(self):
        class Fixtures(unittest.TestCase):
            def test_ok(self):pass
            def test_bad(self):self.fail('private assertion content')
            def test_sub(self):
                with self.subTest(value='private subtest value'):self.assertEqual(1,2)
        text=io.StringIO()
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=partial(ProgressResult,progress=writer(text))).run(unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
        self.assertFalse(result.wasSuccessful())
        rows=[json.loads(line) for line in text.getvalue().splitlines()]
        endings=[row for row in rows if row['event']=='test_finished']
        self.assertEqual(len(endings),3)
        self.assertEqual({r['status'] for r in endings},{'passed','failed','failed_subtest'})
        self.assertNotIn('private',text.getvalue())

    def test_offline_entrypoint_creates_default_progress_log(self):
        from tests import run_offline
        class Fixture(unittest.TestCase):
            def runTest(self):pass
        suite=unittest.TestSuite([Fixture()])
        with tempfile.TemporaryDirectory() as folder,patch.object(run_offline,'ROOT',Path(folder)),patch('unittest.TestLoader.discover',return_value=suite),redirect_stdout(io.StringIO()):
            self.assertEqual(run_offline.main(),0)
            logs=list((Path(folder)/'outputs/logs').glob('offline-tests-*.jsonl'))
            self.assertEqual(len(logs),1)
            rows=[json.loads(line) for line in logs[0].read_text().splitlines()]
            self.assertEqual(rows[0]['event'],'run_started')
            self.assertEqual(rows[-1]['event'],'run_finished')
            self.assertEqual(rows[-1]['status'],'passed')

    def test_provider_category_is_saved_without_private_error_body(self):
        from agent.provider_errors import ProviderError
        with tempfile.TemporaryDirectory() as folder,patch('agent.runtime.execution_log.APPLICATION_ROOT',Path(folder)),redirect_stdout(io.StringIO()):
            with self.assertRaises(ProviderError):
                with timer('LLM request'):raise ProviderError('groq','RATE_LIMIT','private-provider-message',status=429)
            text=next((Path(folder)/'outputs/logs').glob('execution-*.jsonl')).read_text()
            end=json.loads(text.splitlines()[-1])
            self.assertEqual(end['category'],'RATE_LIMIT');self.assertEqual(end['http_status'],429)
            self.assertNotIn('private-provider-message',text)
