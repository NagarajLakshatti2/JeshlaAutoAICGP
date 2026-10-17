"""Real local file/SQLite tests with a fake model; no hosted API calls."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from openpyxl import Workbook
from agent.tools.table_tools import TableTools
from agent.memory.long_term_memory import LongTermMemory
from agent.conversation import answer_question, validate_tool_arguments


class TableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.tools=TableTools(self.root)
        with (self.root/"people.csv").open("w",newline="",encoding="utf-8") as f:
            writer=csv.writer(f);writer.writerows([["Name","Years"],["Ada","4.5"],["Ben","2"],["Cy","unknown"]])
        wb=Workbook();ws=wb.active;ws.title="Team"
        ws.append(["Report title"]);ws.append(["Name","Years"]);ws.append(["Ada",4.5])
        wb.create_sheet("Other").append(["Key","Value"])
        wb.save(self.root/"team.xlsx");wb.close()

    def test_discovery(self):
        self.assertEqual(self.tools.list_tables()["files"],["people.csv","team.xlsx"])

    def test_numeric_filter_and_source_row(self):
        result=self.tools.search_table("people.csv",column="Years",operator="gt",value="3")
        self.assertEqual(result["rows"][0]["values"]["Name"],"Ada")
        self.assertEqual(result["rows"][0]["row"],2)
        self.assertEqual(len(result["rows"]),1)
        self.assertFalse(result["truncated"])

    def test_xlsx_sheet_choice_and_header(self):
        self.assertEqual(self.tools.search_table("team.xlsx")["sheets"],["Team","Other"])
        result=self.tools.search_table("team.xlsx",sheet="Team",header_row=2,query="Ada")
        self.assertEqual(result["rows"][0]["row"],3)
        self.assertEqual(result["sheet"],"Team")

    def test_unknown_column_does_not_silently_match(self):
        result=self.tools.search_table("people.csv",column="Missing",value="Ada")
        self.assertIn("error",result);self.assertEqual(result["columns"],["Name","Years"])

    def test_result_limit_is_explicit(self):
        result=self.tools.search_table("people.csv",limit=1)
        self.assertTrue(result["truncated"]);self.assertEqual(len(result["rows"]),1)

    def test_path_and_filter_rejections(self):
        for path in ["../people.csv",str(self.root/"people.csv"),".env.csv"]:
            with self.assertRaises(ValueError):self.tools.search_table(path)
        for args in [{"operator":"gt"},{"column":"Years"},{"column":"Years","operator":"gt","value":"NaN"}]:
            with self.assertRaises(ValueError):self.tools.search_table("people.csv",**args)
        with self.assertRaises(ValueError):
            validate_tool_arguments("search_memory",{"query":"name","user_id":"other"})
        with self.assertRaises(ValueError):
            validate_tool_arguments("search_table",{"relative_path":"people.csv","operator":"execute"})

    def test_table_evidence_reaches_model(self):
        calls=[]
        def model(messages,specs):
            calls.append(messages.copy())
            if len(calls)==1:
                return {"role":"assistant","content":"","tool_calls":[{"id":"table-1","type":"function","function":{"name":"search_table","arguments":json.dumps({"relative_path":"people.csv","query":"Ada"})}}]}
            return {"role":"assistant","content":"Ada: 4.5 years (people.csv, row 2)."}
        result=answer_question({"question":"Find Ada in people.csv","route":"rag"},model=model,
                               project_root=self.root,document_search=lambda query:None,tools=self.tools)
        evidence=json.loads(calls[1][-1]["content"])
        self.assertEqual(evidence["rows"][0]["row"],2)
        self.assertIn("row 2",result["answer"])


class MemorySearchTests(unittest.TestCase):
    def test_relevance_and_scope_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/"memory.sqlite3"
            with LongTermMemory(db) as memory:
                memory.save("u","project","project_name","JeshlaAutoAI")
                memory.save("u","project","food","rice")
                memory.save("other","project","project_name","PrivateOther")
                memory.save("u","elsewhere","project_name","PrivateSpace")
            with LongTermMemory(db) as memory:
                rows=memory.search("u","project","project name")
                self.assertEqual([row["value"] for row in rows],["JeshlaAutoAI"])
                self.assertEqual(memory.search("u","project","unmatched"),[])
                memory.delete("u","project","project_name")
                self.assertEqual(memory.search("u","project","project name"),[])

    def test_memory_tool_reaches_model(self):
        with LongTermMemory(":memory:") as memory:
            memory.save("u","p","build_tool","Gradle")
            calls=[]
            def model(messages,specs):
                calls.append(messages.copy())
                if len(calls)==1:
                    return {"role":"assistant","content":"","tool_calls":[{"id":"memory-1","type":"function","function":{"name":"search_memory","arguments":'{"query":"build"}'}}]}
                return {"role":"assistant","content":"Your saved build tool is Gradle."}
            result=answer_question({"question":"What build tool?"},model=model,
                                   project_root=Path(__file__).resolve().parents[1],document_search=lambda query:None,
                                   memory_search=lambda query,limit=20:{"facts":memory.search("u","p",query,limit)})
            self.assertIn("Gradle",calls[1][-1]["content"])
            self.assertIn("Gradle",result["answer"])
