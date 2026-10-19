import unittest,json
from types import SimpleNamespace
from unittest.mock import patch
from rag.retrieval import document_sources,execute_search_documents
from agent.citation_guard import visible_document_refs,document_citation_issue
import test_conversation_sources as source_tests

class DocumentSourceTests(unittest.TestCase):
    def sample(self):
        doc=SimpleNamespace(page_content="Useful indexed evidence "*100,metadata={"source":"sample.pdf","page":2,"file_type":"pdf"})
        return document_sources([((doc,1.0,"BM25"),1.0)])
    def test_stable_bounded_reference_and_metadata(self):
        result=self.sample();row=result["sources"][0]
        self.assertEqual(row["ref"],self.sample()["sources"][0]["ref"])
        self.assertEqual(row["source"],"sample.pdf");self.assertEqual(row["location"],"2")
        self.assertEqual(row["location_kind"],"page");self.assertTrue(row["truncated"])
        self.assertEqual(len(row["text"]),1800)
    def test_only_visible_nonempty_records_validate(self):
        result=self.sample();refs=visible_document_refs(result,json.dumps(result,ensure_ascii=False))
        ref=result["sources"][0]["ref"]
        self.assertEqual(refs,{ref});self.assertIsNone(document_citation_issue('Source ['+ref+']',refs))
        self.assertIsNotNone(document_citation_issue('[DOC-invented]',refs))
        self.assertEqual(visible_document_refs(result,'not visible'),set())
    def test_keyword_path_does_not_load_embeddings_and_text_stays_compatible(self):
        doc=SimpleNamespace(page_content="Indexed topic",metadata={"source":"topic.txt","page":1})
        with patch('rag.retrieval._load_resources',side_effect=AssertionError('No embeddings')),patch('rag.retrieval.bm25_search',return_value=[(doc,2.0)]),patch('rag.retrieval._load_keyword_resources',return_value=(None,[doc])):
            self.assertIn('SOURCE 1',execute_search_documents('topic',retrieval_mode='keyword'))
            self.assertEqual(execute_search_documents('topic',retrieval_mode='keyword',structured=True)['sources'][0]['source'],'topic.txt')
    def test_document_reference_correction_in_loop(self):
        evidence=self.sample();ref=evidence['sources'][0]['ref']
        result,_=source_tests.ConversationTests().run_answer([
            {'action':'search_documents','arguments':{'query':'topic'}},
            {'action':'finish','answer':'[DOC-fake]'},
            {'action':'finish','answer':'Evidence ['+ref+'] sample.pdf page 2.'}],documents=lambda **kwargs:evidence)
        self.assertIn(ref,result['answer'])
    def test_empty_structured_search_stops_grounded_claim(self):
        result,_=source_tests.ConversationTests().run_answer([
            {'action':'search_documents','arguments':{'query':'topic'}},
            {'action':'finish','answer':'Invented document fact.'}],state={'question':'My indexed document','route':'rag'},documents=lambda **kwargs:{'sources':[]})
        self.assertEqual(result['task_status'],'incomplete');self.assertNotIn('Invented',result['answer'])
