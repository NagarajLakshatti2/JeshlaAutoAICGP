import unittest
from agent.interfaces.attachments import extract_attachment,attachment_question

class AttachmentTests(unittest.TestCase):
    def test_text_limits_and_name_are_explicit(self):
        item=extract_attachment("C:\\private\\notes.md",("alpha "*3000).encode())
        self.assertEqual(item["name"],"notes.md")
        self.assertEqual(len(item["text"]),12000)
        self.assertTrue(item["truncated"])
        prompt=attachment_question("Summarize",item)
        self.assertIn("untrusted data",prompt)
        self.assertIn('"limited": true',prompt)
        self.assertEqual(attachment_question("hello",None),"hello")

    def test_rejected_uploads(self):
        for name,data in [("script.exe",b"x"),("file.txt",b""),("file.txt",b"x"*1000001),("file.txt",b"\xff")]:
            with self.subTest(name=name,size=len(data)):
                with self.assertRaises(ValueError):extract_attachment(name,data)

    def test_utf8_bom_is_supported(self):
        self.assertEqual(extract_attachment("file.txt",b"\xef\xbb\xbfhello")["text"],"hello")

    def test_optional_docx_extracts_paragraphs_and_tables(self):
        import io
        try:from docx import Document
        except ImportError:self.skipTest("Optional DOCX reader not installed")
        document=Document();document.add_paragraph("Document paragraph")
        document.add_table(rows=1,cols=1).cell(0,0).text="Table evidence"
        data=io.BytesIO();document.save(data)
        item=extract_attachment("sample.docx",data.getvalue())
        self.assertIn("Document paragraph",item["text"])
        self.assertIn("Table evidence",item["text"])

    def test_optional_pdf_blank_has_no_readable_text(self):
        import io
        try:from pypdf import PdfWriter
        except ImportError:self.skipTest("Optional PDF reader not installed")
        writer=PdfWriter();writer.add_blank_page(width=100,height=100)
        data=io.BytesIO();writer.write(data)
        with self.assertRaisesRegex(ValueError,"No readable text"):
            extract_attachment("blank.pdf",data.getvalue())

    def test_memory_commands_do_not_absorb_attachment(self):
        item={"name":"notes.txt","text":"Unrelated document text","truncated":False}
        for command in ["REMEMBER format = PDF","FORGET format","SHOW MEMORY","MEMORY HISTORY format","SESSION default","LIST CHATS"]:
            self.assertEqual(attachment_question(command,item),command)
        self.assertIn("Unrelated document text",attachment_question("Summarize my notes",item))

    def test_excel_values_and_limits(self):
        import io
        try:from openpyxl import Workbook
        except ImportError:self.skipTest("Optional Excel reader not installed")
        book=Workbook();sheet=book.active;sheet.title="Results"
        sheet.append(["Tool","Status"]);sheet.append(["Playwright","Y"])
        sheet.cell(101,1,"Outside row limit")
        data=io.BytesIO();book.save(data);book.close()
        result=extract_attachment("results.xlsx",data.getvalue())
        self.assertIn("Sheet: Results",result["text"])
        self.assertIn("Playwright",result["text"])
        self.assertNotIn("Outside row limit",result["text"])
        self.assertTrue(result["truncated"])

    def test_excel_formula_only_requires_cached_values(self):
        import io
        try:from openpyxl import Workbook
        except ImportError:self.skipTest("Optional Excel reader not installed")
        book=Workbook();book.active["A1"]="=1+1"
        data=io.BytesIO();book.save(data);book.close()
        with self.assertRaisesRegex(ValueError,"cached values"):
            extract_attachment("formulas.xlsx",data.getvalue())
