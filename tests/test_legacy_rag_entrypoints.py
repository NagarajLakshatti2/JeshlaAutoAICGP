"""Legacy commands forward to the shared console before historical model/sample code."""
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType
from unittest.mock import Mock,patch
import unittest

class LegacyRagEntryTests(unittest.TestCase):
    def check_entry(self, name, package):
        root=Path(__file__).resolve().parents[1]
        canonical=ModuleType('agent.langgraph.langgraph_agent')
        calls=[]
        canonical.main=lambda:calls.append(sys.argv.copy())
        blocked=ModuleType('langchain_huggingface')
        arguments=[name,'--session','compatibility-check','--input-mode','end']
        with tempfile.TemporaryDirectory() as folder:
            previous=Path.cwd()
            try:
                os.chdir(folder)
                with patch.dict(sys.modules,{'agent.langgraph.langgraph_agent':canonical,'langchain_huggingface':blocked}),patch.object(sys,'argv',arguments.copy()),patch.object(sys,'path',[str(root/'rag'),str(root),*sys.path]):
                    with self.assertRaises(SystemExit) as exit:
                        if package:runpy.run_module('rag.'+name,run_name='__main__')
                        else:runpy.run_path(str(root/'rag'/(name+'.py')),run_name='__main__')
                    self.assertEqual(exit.exception.code,0)
                self.assertEqual(len(calls),1)
                self.assertEqual(calls[0][1:],arguments[1:])
                self.assertEqual(list(Path(folder).iterdir()),[])
            finally:os.chdir(previous)

    def test_package_commands_forward_once_without_loading_legacy_models(self):
        for name in ['rag_agent','tool_calling','web_search_agent']:
            with self.subTest(command=name):self.check_entry(name,True)

    def test_standalone_commands_forward_from_unrelated_folder(self):
        for name in ['rag_agent','tool_calling','web_search_agent']:
            with self.subTest(command=name):self.check_entry(name,False)
