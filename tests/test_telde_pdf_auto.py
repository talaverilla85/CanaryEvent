"""Tests for Telde PDF extraction routing; no actual paid API calls."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_auto as auto
import telde_pdf_vision as tv

OFFICIAL="https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf"
INDEX={"programs":[{"pdf_url":OFFICIAL,"year":2026,"title":"Fiestas Caserones Altos 2026"}]}

class FakePage:
    def __init__(self,text):self.text=text
    def extract_text(self):return self.text

class FakeReader:
    def __init__(self,*args,**kwargs):self.pages=[FakePage("")]

class AutoTeldePdfTests(unittest.TestCase):
    def test_select_recent_only_official_dates(self):
        docs={"programs":[
            *INDEX["programs"],
            {"pdf_url":"https://www.telde.es/wp-content/uploads/2026/04/viejo.pdf","year":2026,"title":"abril"},
            {"pdf_url":"https://www.telde.es/wp-content/uploads/2026/09/sanfrancisco26.pdf","year":2026,"title":"San Francisco"}
        ]}
        result=auto.choose_recent(docs,dt.date(2026,10,27),None,3)
        self.assertEqual(len(result),2)
        self.assertIn("caseronesaltos26.pdf",result[0]["pdf_url"])
        named=auto.choose_recent(docs,dt.date(2026,10,27),"sanfrancisco26.pdf",1)
        self.assertIn("sanfrancisco26",named[0]["pdf_url"])

    def test_native_text_only_if_date_hour_event_same_line(self):
        text="07 de noviembre 20:30 - Concierto de música tradicional en la plaza"
        candidate=auto.text_candidates(text,2026)
        self.assertEqual(len(candidate),1)
        self.assertEqual(candidate[0]["date"],"2026-11-07")
        self.assertEqual(candidate[0]["time"],"20:30")
        self.assertTrue(auto.verify_text_evidence(text,candidate[0]))
        self.assertEqual(auto.text_candidates("Fiestas octubre: plaza mayor",2026),[])
        self.assertFalse(auto.verify_text_evidence(text,{"evidence":"La fecha inventada 8 noviembre"}))

    def test_no_key_scanned_pdf_requires_vision_no_spend(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"index.json").write_text(json.dumps(INDEX),encoding="utf8")
            with patch.object(auto,"REVIEW",p/"pending.json"), \
                 patch.object(auto,"STATE",p/"state.json"), \
                 patch.object(auto,"CACHE",p/"cache.json"), \
                 patch.object(auto,"REPORT",p/"report.json"), \
                 patch.object(tv,"SOURCE",p/"index.json"), \
                 patch.object(tv,"official_robots",return_value=object()), \
                 patch.object(tv,"download_pdf",return_value=(p/"dummy.pdf","f"*64,42)), \
                 patch.object(auto,"PdfReader",FakeReader), \
                 patch.dict(os.environ,{"OPENAI_API_KEY":""}):
                r=auto.run(["--filename","caseronesaltos26.pdf","--api"],today=dt.date(2026,10,27))
                self.assertEqual(r["api_calls"],0)
                self.assertEqual(r["docs"][0]["inspected"][0]["route"],"ai_vision")
                self.assertEqual(r["docs"][0]["inspected"][0]["status"],"requires_openai_api_key")
                self.assertEqual(json.loads((p/"pending.json").read_text()),[])
                self.assertEqual(json.loads((p/"state.json").read_text()),{} if False else json.loads((p/"state.json").read_text()))

    def test_scanned_pdf_uses_api_once_and_never_auto_publishes(self):
        rec={"title":"Concierto de música popular","date":"2026-11-07",
             "time":"20:30","venue":"Plaza de Caserones Altos",
             "evidence":"7 noviembre 20:30 concierto de música popular",
             "type":"musica"}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"index.json").write_text(json.dumps(INDEX),encoding="utf8")
            with patch.object(auto,"REVIEW",p/"pending.json"), \
                 patch.object(auto,"STATE",p/"state.json"), \
                 patch.object(auto,"CACHE",p/"cache.json"), \
                 patch.object(auto,"REPORT",p/"report.json"), \
                 patch.object(tv,"SOURCE",p/"index.json"), \
                 patch.object(tv,"official_robots",return_value=object()), \
                 patch.object(tv,"download_pdf",return_value=(p/"dummy.pdf","c"*64,42)), \
                 patch.object(auto,"PdfReader",FakeReader), \
                 patch.object(tv,"render_page_jpeg",return_value=(b"fakepng",(500,800))), \
                 patch.object(tv,"call_openai_vision",return_value=(
                     {"events":[rec],"page_is_program":True},
                     {"input_tokens":1000,"output_tokens":500})) as call, \
                 patch.dict(os.environ,{"OPENAI_API_KEY":"test-key"}):
                r=auto.run(["--filename","caseronesaltos26.pdf","--api"],today=dt.date(2026,10,27))
                self.assertEqual(r["api_calls"],1)
                call.assert_called_once()
                content=json.loads((p/"pending.json").read_text(encoding="utf8"))
                self.assertEqual(len(content),1)
                self.assertEqual(content[0]["review_status"],"pending_review")
                self.assertEqual(content[0]["date_state"],"upcoming")
                self.assertEqual(content[0]["extractor"],"ai_vision")
                self.assertEqual(content[0]["pdf_page"],1)
                # A second run does not charge the API again for this page.
                again=auto.run(["--filename","caseronesaltos26.pdf","--api"],today=dt.date(2026,10,27))
                self.assertEqual(again["api_calls"],0)
                call.assert_called_once()

    def test_workflow_never_exposes_key_in_browser(self):
        wf=(ROOT/".github/workflows/sync-events.yml").read_text(encoding="utf8")
        self.assertIn("secrets.OPENAI_API_KEY",wf)
        self.assertIn("telde_pdf_auto.py --api",wf)
        self.assertIn('if [[ -n "$OPENAI_API_KEY" ]]',wf)
        self.assertNotIn("OPENAI_API_KEY", (ROOT/"public/index.html").read_text(encoding="utf8"))

if __name__=="__main__":
    unittest.main()
