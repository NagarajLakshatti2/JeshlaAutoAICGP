"""Source consistency measures text changes without exporting source contents."""
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from unittest.mock import patch
from docx import Document
from rag.source_audit import audit_sources

def chunk(source,text,page=1):
 return SimpleNamespace(page_content=text,metadata={'source':source,'page':page})

class SourceAuditTests(unittest.TestCase):
 def test_changed_source_is_mismatch_not_verified_fresh(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p=root/'notes.txt';p.write_text('Report format is PDF.',encoding='utf-8')
   old=[chunk('notes.txt','Report format is PDF.')]
   self.assertEqual(audit_sources(old,root)['counts']['matches_current_text'],1)
   p.write_text('Report format is HTML.',encoding='utf-8')
   result=audit_sources(old,root)
   self.assertEqual(result['counts']['text_mismatch'],1)
   self.assertEqual(result['status'],'P')
   self.assertNotIn('Report format',str(result))

 def test_missing_source_and_location_remain_unverified(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'notes.txt').write_text('A valid passage.',encoding='utf-8')
   result=audit_sources([chunk('absent.txt','old'),chunk('notes.txt','passage',page=9)],root)
   self.assertEqual(result['counts']['unverified'],2)
   self.assertEqual({row['reason'] for row in result['cases']},{'source_missing','location_missing'})

 def test_traversal_is_not_read_and_size_bound_is_explicit(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'large.txt').write_text('private-source-text',encoding='utf-8')
   with patch('rag.source_audit.read_locations',side_effect=AssertionError('Must not read')):
    result=audit_sources([chunk('../outside.txt','text'),chunk('large.txt','text')],root,max_file_bytes=1)
   self.assertEqual(result['counts']['unverified'],2)
   self.assertEqual({row['reason'] for row in result['cases']},{'invalid_source_name','file_size_limit'})

 def test_real_docx_and_multiline_csv_record_locations(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);doc=Document();doc.add_paragraph('Current document evidence.');doc.save(root/'notes.docx')
   (root/'rows.csv').write_text('Name,Detail\nAda,"first line\nsecond line"\nBen,third\n',encoding='utf-8')
   result=audit_sources([chunk('notes.docx','document evidence.'),chunk('rows.csv','Name: Ben\nDetail: third',page=3)],root)
   self.assertEqual(result['counts']['matches_current_text'],2)

 def test_sample_cap_and_new_files_do_not_claim_full_coverage(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'a.txt').write_text('known',encoding='utf-8');(root/'new.txt').write_text('new evidence',encoding='utf-8')
   result=audit_sources([chunk('a.txt','known'),chunk('a.txt','known')],root,max_chunks=1)
   self.assertTrue(result['coverage_truncated']);self.assertEqual(result['status'],'P')
   self.assertIn('new.txt',result['supported_files_without_indexed_chunks'])
