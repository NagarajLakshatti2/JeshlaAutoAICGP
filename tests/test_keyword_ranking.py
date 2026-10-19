import unittest
from types import SimpleNamespace
from unittest.mock import patch
from rag.retrieval import keyword_tokens,bm25_search,_normalized_keyword_resources,document_sources

class KeywordRankingTests(unittest.TestCase):
    def test_possessive_punctuation_and_function_words(self):
        self.assertEqual(keyword_tokens("When did Sam's team use API-tests?"),["sam","team","use","api","tests"])
        self.assertEqual(keyword_tokens("WHO IS THE?"),[])
    def test_source_terms_and_topic_match_without_embeddings(self):
        chunks=[SimpleNamespace(page_content="Regression checks are supported.",metadata={"source":"Project_Orion.pdf","page":1}),SimpleNamespace(page_content="Fruit apples oranges.",metadata={"source":"recipes.txt","page":1}),SimpleNamespace(page_content="Bicycle wheels chains.",metadata={"source":"transport.txt","page":1})]
        _normalized_keyword_resources.cache_clear()
        try:
            with patch('rag.retrieval._load_keyword_resources',return_value=(None,chunks)),patch('rag.retrieval._load_resources',side_effect=AssertionError('No model')):
                hits=bm25_search('Orion: regression?',normalized=True)
                self.assertEqual(hits[0][0].metadata['source'],'Project_Orion.pdf')
                self.assertEqual(bm25_search('!!!',normalized=True),[])
        finally:_normalized_keyword_resources.cache_clear()
    def test_neighbor_context_never_crosses_source_or_page(self):
        def doc(text,source='a.pdf',page=1):return SimpleNamespace(page_content=text,metadata={'source':source,'page':page,'file_type':'pdf'})
        current=doc('Core text.');neighbor=doc('Adjacent evidence.');other=doc('PRIVATE OTHER PAGE',page=2)
        r=document_sources([((current,1.,'BM25'),1.)],context_chunks=[current,neighbor,other])
        self.assertIn('Adjacent evidence',r['sources'][0]['text'])
        self.assertNotIn('PRIVATE',r['sources'][0]['text'])
