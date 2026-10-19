import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from agent.memory.long_term_memory import LongTermMemory
from agent.conversation import answer_question
from agent.tools.project_tools import ProjectTools
from rag.retrieval import document_sources

class MixedGroundingTests(unittest.TestCase):
    def test_scoped_memory_document_and_page_evidence_reach_one_answer(self):
        with tempfile.TemporaryDirectory() as folder,LongTermMemory(":memory:") as memory:
            root=Path(folder);path=root/"design.txt";path.write_text("UI automation uses Playwright Java.",encoding="utf-8")
            memory.save("u","p","project_name","ExampleProject",source_kind="user_statement")
            memory.save("other","p","project_name","PRIVATE_OTHER")
            evidence=document_sources([((SimpleNamespace(page_content=path.read_text(),metadata={"source":"design.txt","page":1,"file_type":"txt"}),1.,"fixture"),1.)])
            ref=evidence["sources"][0]["ref"];captured=[];step=0
            def call(name,args,identifier):return {"tool_calls":[{"id":identifier,"function":{"name":name,"arguments":json.dumps(args)}}]}
            replies=[call("search_memory",{"query":"project"},"memory"),call("search_documents",{"query":"UI automation","mode":"keyword"},"docs"),call("web_search",{"query":"public Playwright Java docs"},"web"),call("fetch_web_page",{"url":"https://example.org/docs"},"page"),{"content":"User-stated project ExampleProject uses Playwright Java ["+ref+"] design.txt section 1. [Public page](https://example.org/docs) describes the API."}]
            def model(messages,tools):captured.append(json.dumps(messages,ensure_ascii=False));return replies.pop(0)
            result=answer_question({"question":"Combine saved facts, indexed design and a public page"},model=model,project_root=root,tools=ProjectTools(root),document_search=lambda **k:evidence,memory_search=lambda query,**k:{"facts":memory.search("u","p",query)},web=lambda **k:{"results":[{"url":"https://example.org/docs","snippet":"Search snippet"}]},page_fetch=lambda url:{"url":url,"text":"Fetched page describes the API."})
            self.assertNotIn("PRIVATE_OTHER",captured[-1])
            self.assertIn("Fetched page describes",captured[-1]);self.assertIn("user_statement",captured[-1])
            self.assertIn(ref,result["answer"]);self.assertIn("https://example.org/docs",result["answer"])
            self.assertNotEqual(result.get("task_status"),"incomplete")
