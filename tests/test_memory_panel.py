import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.interfaces.memory_panel import fact_rows
from agent.interfaces.browser import BrowserBackend
from agent.memory.long_term_memory import LongTermMemory

class MemoryPanelTests(unittest.TestCase):
    def test_legacy_text_keeps_value_and_metadata_separate(self):
        rows=fact_rows('- report: "PDF" | metadata: {"source_kind":"user_statement","verification_status":"unverified"}')
        self.assertEqual(rows[0]['value'],'PDF');self.assertEqual(rows[0]['source_kind'],'user_statement')
    def test_structured_read_is_scoped_without_seed_or_model(self):
        with tempfile.TemporaryDirectory() as folder,patch('agent.interfaces.browser.ROOT',Path(folder)):
            path=Path(folder)/'outputs/memory/long_term_memory.sqlite3'
            with LongTermMemory(path) as store:
                store.save('u','p','fact','mine');store.save('other','p','fact','private')
            backend=BrowserBackend.__new__(BrowserBackend);backend.user='u';backend.space='p'
            self.assertEqual([row['value'] for row in backend.memory_records()],['mine'])

    def test_memory_editor_builds_exact_commands_and_rejects_invalid_input(self):
        backend=BrowserBackend.__new__(BrowserBackend)
        with patch.object(backend,'submit',return_value={'answer':'saved'}) as submit:
            backend.edit_memory('default','save','report_format',' PDF ')
            submit.assert_called_once_with('default','REMEMBER report_format = PDF')
            backend.edit_memory('default','forget','report_format')
            self.assertEqual(submit.call_args.args,('default','FORGET report_format'))
            for operation,key,value in [('save','bad key','x'),('save','valid',''),('save','valid','x'*2001),('other','valid','x')]:
                before=submit.call_count
                with self.assertRaises(ValueError):backend.edit_memory('default',operation,key,value)
                self.assertEqual(submit.call_count,before)
