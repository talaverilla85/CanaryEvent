"""Oversized documents must be visible but must not block other official PDFs."""
import datetime as dt
import json
import os
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_auto as auto
import telde_pdf_vision as tv

BIG="https://www.telde.es/wp-content/uploads/2026/10/large-program.pdf"
SMALL="https://www.telde.es/wp-content/uploads/2026/10/small-program.pdf"
DOCS=[{"pdf_url":BIG,"year":2026,"title":"Fiestas Grandes"},
      {"pdf_url":SMALL,"year":2026,"title":"Fiestas Pequeñas"}]

class BlankPage:
    def extract_text(self):return ""

class Reader:
    def __init__(self,*args,**kwargs):self.pages=[BlankPage()]

class OversizeHandlingTests(unittest.TestCase):
    def test_large_file_does_not_prevent_other_doc_and_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"index.json").write_text(json.dumps({"programs":DOCS}),encoding="utf8")
            called=[]
            def download(session,url,robots,cache_dir):
                called.append(url)
                if url==BIG:raise tv.PdfTooLargeError("PDF exceeds size limit")
                return p/"dummy.pdf", "f"*64, 4312
            patches=[
                patch.object(auto,"REVIEW",p/"pending.json"),
                patch.object(auto,"STATE",p/"state.json"),
                patch.object(auto,"CACHE",p/"cache.json"),
                patch.object(auto,"REPORT",p/"report.json"),
                patch.object(auto,"VERIFIED",p/"verified.json"),
                patch.object(tv,"SOURCE",p/"index.json"),
                patch.object(tv,"official_robots",return_value=object()),
                patch.object(tv,"download_pdf",side_effect=download),
                patch.object(auto,"PdfReader",Reader),
                patch.object(auto,"choose_recent",return_value=DOCS),
                patch.dict(os.environ,{"OPENAI_API_KEY":""}),
            ]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for context in patches:stack.enter_context(context)
                first=auto.run(["--max-docs","2"],today=dt.date(2026,10,28))
                self.assertEqual(called,[BIG,SMALL])
                self.assertEqual(len(first["docs"]),1)
                self.assertEqual(first["docs"][0]["pdf_url"],SMALL)
                self.assertEqual(first["api_calls"],0)
                self.assertEqual(len(first["deferred_docs"]),1)
                self.assertEqual(first["deferred_docs"][0]["reason"],"pdf_oversize")
                self.assertEqual(first["deferred_docs"][0]["max_bytes"],tv.MAX_PDF_BYTES)
                self.assertEqual(first["deferred_docs"][0]["resume_on"],"2026-11-04")
                state=json.loads((p/"state.json").read_text(encoding="utf8"))
                self.assertEqual(state[auto.priority.doc_id(BIG)]["defer_reason"],"pdf_oversize")
                self.assertFalse(state[auto.priority.doc_id(BIG)].get("complete",False))
                self.assertIn("pdf_oversize",(p/"report.json").read_text(encoding="utf8"))
                called.clear()
                again=auto.run(["--max-docs","2"],today=dt.date(2026,10,29))
                self.assertNotIn(BIG,called)
                self.assertTrue(any(d["reason"]=="pdf_oversize" for d in again["deferred_docs"]))
                called.clear()
                later=auto.run(["--max-docs","2"],today=dt.date(2026,11,4))
                self.assertIn(BIG,called)
                self.assertTrue(any(d["reason"]=="pdf_oversize" for d in later["deferred_docs"]))

if __name__=="__main__":
    unittest.main()
