"""RAG commands use one index location and never index merely on import."""
import importlib
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
from types import ModuleType,SimpleNamespace
from unittest.mock import Mock,patch
import unittest

class RagPathTests(unittest.TestCase):
    def test_imports_from_unrelated_folder_do_not_load_models_or_write(self):
        root=Path(__file__).resolve().parents[1]
        code='''import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'langchain_huggingface','sentence_transformers','langchain_community'}: raise AssertionError('Models must not load on import')
sys.meta_path.insert(0,Block())
import rag.ingest,rag.csv_search,rag.xlsx_search
from rag.paths import DATA_FOLDER,RAG_DIR
assert DATA_FOLDER==RAG_DIR/'data'
assert rag.csv_search.DATA_FOLDER==DATA_FOLDER==rag.xlsx_search.DATA_FOLDER
print('ok')
'''
        with tempfile.TemporaryDirectory() as folder:
            env=dict(os.environ,PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1')
            result=subprocess.run([sys.executable,'-c',code],cwd=folder,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(list(Path(folder).iterdir()),[])

    def model_stubs(self):
        hf=ModuleType('langchain_huggingface');hf.HuggingFaceEmbeddings=Mock(return_value=object())
        vs=ModuleType('langchain_community.vectorstores');vs.FAISS=Mock()
        vector=Mock();vs.FAISS.from_documents.return_value=vector
        splitters=ModuleType('langchain_text_splitters');splitters.RecursiveCharacterTextSplitter=Mock()
        splitters.RecursiveCharacterTextSplitter.return_value.split_documents.side_effect=lambda documents:list(documents)
        docs=ModuleType('langchain_core.documents');docs.Document=SimpleNamespace
        return {'langchain_huggingface':hf,'langchain_community.vectorstores':vs,'langchain_text_splitters':splitters,'langchain_core.documents':docs},hf,vs,vector

    def test_explicit_ingestion_outputs_match_requested_index_folder(self):
        from rag.ingest import create_vector_db
        stubs,hf,vs,vector=self.model_stubs()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'documents';data.mkdir();out=root/'indexes'
            (data/'notes.txt').write_text('The project uses stable selectors and readable reports.',encoding='utf-8')
            (data/'rows.csv').write_text('Name,Amount\nAda,7\n',encoding='utf-8')
            with patch.dict(sys.modules,stubs):create_vector_db(data_folder=data,index_folder=out)
            with (out/'chunks.pkl').open('rb') as handle:chunks=pickle.load(handle)
            self.assertEqual({c.metadata['source'] for c in chunks},{'notes.txt','rows.csv'})
            row=next(c for c in chunks if c.metadata['source']=='rows.csv')
            self.assertEqual(row.metadata['row'],2)
            self.assertTrue((out/'bm25.pkl').is_file())
            vector.save_local.assert_called_once_with(str(out/'faiss_db'))
            hf.HuggingFaceEmbeddings.assert_called_once()
            self.assertFalse((data/'bm25.pkl').exists())

    def test_empty_input_leaves_existing_indexes_unchanged(self):
        from rag.ingest import create_vector_db
        stubs,hf,vs,vector=self.model_stubs()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'empty';data.mkdir();out=root/'indexes';out.mkdir();index=out/'chunks.pkl';index.write_bytes(b'preserved')
            with patch.dict(sys.modules,stubs),self.assertRaisesRegex(ValueError,'No readable'):
                create_vector_db(data_folder=data,index_folder=out)
            self.assertEqual(index.read_bytes(),b'preserved')
            hf.HuggingFaceEmbeddings.assert_not_called();vector.save_local.assert_not_called()

    def test_default_paths_agree_with_active_retriever(self):
        from rag.paths import RAG_DIR,DATA_FOLDER,FAISS_DB_FOLDER,BM25_FILE,CHUNKS_FILE
        from rag.retrieval import DATA_DIR
        self.assertEqual(RAG_DIR,DATA_DIR)
        self.assertEqual([FAISS_DB_FOLDER,BM25_FILE,CHUNKS_FILE],[DATA_DIR/'faiss_db',DATA_DIR/'bm25.pkl',DATA_DIR/'chunks.pkl'])
        self.assertEqual(DATA_FOLDER,DATA_DIR/'data')
