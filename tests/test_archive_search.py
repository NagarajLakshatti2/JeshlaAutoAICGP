import json,tempfile,unittest
from pathlib import Path
from agent.chat_catalog import ChatCatalog
from agent.conversation import answer_question,validate_tool_arguments
from agent.tools.project_tools import ProjectTools

class ArchiveSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=self.root/"chats.sqlite3"
        self.catalog=ChatCatalog(self.path,"u","p")
        for name in ["one","two"]:self.catalog.register(name)
        self.catalog.append("one","Need a PDF report","Folder undecided.")
        self.catalog.append("two","Need a PDF report","Other chat.")
        for user,space in [("other","p"),("u","other")]:
            other=ChatCatalog(self.path,user,space);other.register("one");other.append("one","PDF report","PRIVATE")

    def test_scope_citations_and_answer_search(self):
        result=self.catalog.search_turns("PDF report",session="one")
        self.assertEqual(len(result["matches"]),1)
        row=result["matches"][0]
        self.assertEqual(row["chat_id"],"one");self.assertIn("turn_id",row);self.assertIn("created_at",row)
        self.assertEqual(len(self.catalog.search_turns("PDF report")["matches"]),2)
        self.assertEqual(len(self.catalog.search_turns("undecided",session="one")["matches"]),1)
        self.assertNotIn("PRIVATE",json.dumps(self.catalog.search_turns("PDF report")))

    def test_bounds_and_literal_parameters(self):
        result=self.catalog.search_turns("PDF",limit=1)
        self.assertEqual(len(result["matches"]),1);self.assertTrue(result["truncated"])
        self.assertEqual(self.catalog.search_turns("PDF",session="one' OR 1=1 --")["matches"],[])
        for query in ["", "!!!", "x"*1501]:
            with self.assertRaises(ValueError):self.catalog.search_turns(query)
        with self.assertRaises(ValueError):self.catalog.search_turns("PDF",limit=0)
        with self.assertRaises(ValueError):validate_tool_arguments("search_chats",{"query":"PDF","user":"other"})

    def test_fake_model_observes_real_archive_evidence(self):
        calls=[]
        def model(messages,specs):
            calls.append(messages.copy())
            if len(calls)==1:return {"role":"assistant","content":"","tool_calls":[{"id":"chat-lookup","function":{"name":"search_chats","arguments":json.dumps({"query":"PDF"})}}]}
            return {"content":"PDF report; historical source is chat one."}
        result=answer_question({"question":"Find my earlier PDF discussion"},model=model,project_root=self.root,document_search=lambda **kwargs:{},tools=ProjectTools(self.root),chat_search=lambda **kwargs:self.catalog.search_turns(session="one",**kwargs))
        evidence=json.loads(calls[1][-1]["content"])
        self.assertEqual(evidence["matches"][0]["chat_id"],"one")
        self.assertIn("historical",result["answer"])

    def test_restart_and_output_bound(self):
        for i in range(15):self.catalog.append("one","PDF "+"x"*3000,"y"*3000)
        reopened=ChatCatalog(self.path,"u","p")
        result=reopened.search_turns("PDF",session="one",limit=20)
        self.assertLess(len(json.dumps(result,ensure_ascii=False)),8000)
        self.assertTrue(result["truncated"])
