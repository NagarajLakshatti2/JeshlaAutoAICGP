"""Structured table grounding through the real read-only conversation loop."""
import json
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
from agent.conversation import answer_question
from agent.tools.table_tools import TableTools

class TableGroundingTests(unittest.TestCase):
    def run_case(self, root, steps):
        replies=iter(steps);seen=[]
        def model(messages, specs):
            seen.append(messages.copy())
            step=next(replies)
            if isinstance(step,str):return {"role":"assistant","content":step}
            name,args=step
            return {"role":"assistant","content":"","tool_calls":[{"id":"call-"+str(len(seen)),"type":"function","function":{"name":name,"arguments":json.dumps(args)}}]}
        return answer_question({"question":"Read my table and cite the source rows.","route":"rag"},model=model,project_root=root,tools=TableTools(root),document_search=lambda **kwargs:{"sources":[]}),seen

    def test_failed_read_cannot_license_invented_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            result,_=self.run_case(Path(folder),[("search_table",{"relative_path":"missing.csv"}),"Invented profit is 900."])
            self.assertEqual(result["task_status"],"incomplete")
            self.assertNotIn("900",result["answer"])

    def test_empty_table_cannot_bypass_empty_indexed_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"empty.csv").write_text("Name,Amount\n",encoding="utf-8")
            result,_=self.run_case(root,[("search_documents",{"query":"profit"}),("search_table",{"relative_path":"empty.csv"}),"Invented profit is 900."])
            self.assertEqual(result["task_status"],"incomplete")
            self.assertNotIn("900",result["answer"])

    def test_real_xlsx_ambiguity_can_be_resolved_before_answering(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);wb=Workbook();ws=wb.active;ws.title="Reports";ws.append(["Report"]);ws.append(["Name","Amount"]);ws.append(["Ada",7]);wb.create_sheet("Other").append(["Name"]);wb.save(root/"reports.xlsx");wb.close()
            result,seen=self.run_case(root,[("search_table",{"relative_path":"reports.xlsx"}),("search_table",{"relative_path":"reports.xlsx","sheet":"Reports","header_row":2,"query":"Ada"}),"Ada: 7 (reports.xlsx, Reports, row 3)."])
            self.assertNotIn("task_status",result)
            self.assertIn("Choose a sheet",seen[1][-1]["content"])
            evidence=json.loads(seen[2][-1]["content"])
            self.assertEqual((evidence["file"],evidence["sheet"],evidence["rows"][0]["row"]),("reports.xlsx","Reports",3))
            self.assertEqual(evidence["rows"][0]["values"]["Amount"],"7")

    def test_real_csv_result_limit_and_source_row_reach_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"rows.csv").write_text("Name,Amount\nAda,7\nBen,8\n",encoding="utf-8")
            result,seen=self.run_case(root,[("search_table",{"relative_path":"rows.csv","limit":1}),"Ada: 7 (rows.csv, row 2). Results were truncated; no total is established."])
            evidence=json.loads(seen[1][-1]["content"])
            self.assertTrue(evidence["truncated"])
            self.assertEqual(evidence["rows"][0]["row"],2)
            self.assertIn("no total",result["answer"])
