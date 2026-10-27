"""An invalid second PDF page must not erase independently verified earlier pages."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import municipal_pdf_auto as auto
import municipal_pdf_sources as sources
import telde_pdf_vision as vision
import telde_pdf_integrity as proof
import telde_pdf_priority as priority

MUNI="Santa Lucía de Tirajana"
URL=sources.SOURCES[MUNI]["known_pdf"]["2026"]
DAY=dt.date(2026,10,27)
SHA="c"*64
ENTRY={"municipality":MUNI,"title":"Fiestas San Rafael","pdf_url":URL,
       "year":2026,"program_end_hint":"2026-11-01",
       "program_end_evidence_url":URL}
FIRST={"title":"Concierto de la Banda Municipal","date":"2026-10-27",
       "time":"20:30","venue":"Plaza de San Rafael",
       "evidence":"27 de octubre a las 20:30 concierto de la Banda Municipal en Plaza de San Rafael",
       "type":"musica","admission_type":"unknown","admission_details":None}
SECOND={**FIRST,"evidence":"27 octubre 20:30 concierto de la Banda Municipal Plaza de San Rafael"}

class Page:
    def __init__(self,text):self.text=text
    def extract_text(self):return self.text
class Reader:
    def __init__(self,*a,**kw):
        self.pages=[Page("27 de octubre 20:30 Concierto de la Banda Municipal en la plaza"),
                    Page("28 de octubre 21:00 Concierto en el recinto")]

class MunicipalResumeTests(unittest.TestCase):
    def test_crashing_later_page_preserves_first_approval_and_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory)
            idx=tmp/"index.json"
            idx.write_text(json.dumps({"programs":[ENTRY]}),encoding="utf8")
            key=f"{SHA}/0/{vision.MODEL}/{auto.VERSION}"
            cache={
                key+"/ai_vision":{"output":{"events":[FIRST],"page_is_program":True}},
                key+"/independent_double_read":{"output":{"events":[SECOND],"page_is_program":True}}
            }
            (tmp/"cache.json").write_text(json.dumps(cache),encoding="utf8")
            loc={"INDEX":idx,"CACHE":tmp/"cache.json","REVIEW":tmp/"review.json",
                 "VERIFIED":tmp/"verified.json","ARCHIVE":tmp/"archive.json",
                 "STATE":tmp/"state.json","REPORT":tmp/"report.json"}
            with ExitStack() as stack:
                for name,path in loc.items():
                    stack.enter_context(patch.object(auto,name,path))
                stack.enter_context(patch.object(auto.sources,"robots_for",return_value=object()))
                stack.enter_context(patch.object(vision,"download_pdf",return_value=(tmp/"not-used.pdf",SHA,20)))
                stack.enter_context(patch.object(auto,"PdfReader",Reader))
                stack.enter_context(patch.object(vision,"render_page_jpeg",return_value=(b"jpeg",(600,800))))
                call=stack.enter_context(patch.object(vision,"call_openai_vision",side_effect=ValueError("bad model response")))
                stack.enter_context(patch.dict(os.environ,{"OPENAI_API_KEY":"test-only"}))
                outcome=auto.run(["--api","--max-pages","2"],today=DAY)
                self.assertEqual(outcome["auto_verified_count"],1)
                self.assertEqual(outcome["api_calls"],1)
                self.assertEqual(outcome["documents"][0]["inspected"][1]["retry_after"],"2026-10-28")
                self.assertEqual(outcome["errors"][0]["pdf_page"],2)
                self.assertEqual(call.call_count,1)
                rows=json.loads((tmp/"verified.json").read_text(encoding="utf8"))
                self.assertEqual(len(rows),1)
                state=json.loads((tmp/"state.json").read_text(encoding="utf8"))
                checkpoint=state[priority.doc_id(URL)]
                self.assertEqual(checkpoint["done_pages"],[0])
                self.assertFalse(checkpoint["complete"])
                self.assertTrue(proof.trusted(rows[0],{URL},state,cache,DAY,
                                               vision.MODEL,auto.VERSION))
                self.assertEqual(len(json.loads((tmp/"review.json").read_text(encoding="utf8"))),1)
                again=auto.run(["--archive-only"],today=DAY)
                self.assertEqual(again["auto_verified_count"],1)

if __name__=="__main__":unittest.main()
