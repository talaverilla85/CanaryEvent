"""Regression tests for three allowlisted official municipal PDF sources."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import municipal_pdf_sources as sources
import municipal_pdf_auto as auto
import telde_pdf_vision as vision
import telde_pdf_verified as verified
import telde_pdf_integrity as integrity

DAY=dt.date(2026,10,27)
ST="Santa Lucía de Tirajana"
URL=sources.SOURCES[ST]["known_pdf"]["2026"]
SHA="f"*64
EVENT={"title":"Concierto de música popular","date":"2026-10-30",
       "time":"21:00","venue":"Recinto Ferial de Vecindario",
       "type":"musica","admission_type":"unknown","admission_details":None,
       "evidence":"30 octubre, concierto de música popular, 21:00 Recinto Ferial de Vecindario"}

class Html:
    status_code=200
    text="User-agent: *\nAllow: /\n"
    content=b""
class FakeHttp:
    def __init__(self,body):self.body=body
    def get(self,url,**kwargs):
        o=Html()
        if "robots.txt" not in url:
            o.content=self.body.encode("utf8")
        return o

class MultiMunicipalPdfTests(unittest.TestCase):
    def test_three_sources_have_strict_official_pdf_urls(self):
        self.assertEqual(set(sources.SOURCES),{"Agüimes","Gáldar",ST})
        for municipio,spec in sources.SOURCES.items():
            good=spec["known_pdf"]["2026"]
            self.assertTrue(sources.verified_pdf(good,municipio,2026))
            self.assertFalse(sources.verified_pdf(good,municipio,2027))
            for bad in (good.replace("https://","http://"),good+"?x=1",
                        good.replace(spec["host"],"evil.example"),
                        good.replace("2026/","2026/10/../../")):
                self.assertFalse(sources.verified_pdf(bad,municipio,2026))

    def test_discovery_ignores_annexes_and_external_pdf(self):
        html=f'''<main>
        <a href="{URL}">Descargar programa de Fiestas San Rafael 2026</a>
        <a href="https://evil.example/san-rafael-programa.pdf">Programa San Rafael</a>
        <a href="https://www.santaluciagc.com/wp-content/uploads/2026/10/anexo.pdf">BASES DE ELECCIÓN ROMERA</a>
        </main>'''
        result=sources.discover(FakeHttp(html),ST,2026)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["pdf_url"],URL)
        self.assertFalse(result[0]["event_date_verified"])

    def test_known_ends_skip_historical_pdf_but_keep_future(self):
        cat=sources.build_catalog(2026,FakeHttp("<main></main>"))
        self.assertGreaterEqual(len(cat["programs"]),3)
        chosen=auto.candidates(cat,DAY,{})
        self.assertEqual(chosen[0]["municipality"],ST)
        self.assertFalse(any(e.get("program_end_hint")=="2026-10-13" for e in chosen))
        self.assertFalse(any(e.get("program_end_hint")=="2026-07-26" for e in chosen))

    def test_existing_telde_decoder_remains_telde_by_default(self):
        url="https://www.telde.es/wp-content/uploads/2026/10/example.pdf"
        x,e=vision.validate_candidate(EVENT,2026,"Ejemplo",url,SHA,1,DAY)
        self.assertIsNone(e)
        self.assertEqual(x["municipality"],"Telde")
        y,e=vision.validate_candidate(EVENT,2026,"San Rafael",URL,SHA,1,DAY,
                                      municipality=ST)
        self.assertIsNone(e)
        self.assertEqual(y["municipality"],ST)
        self.assertTrue(y["id"].startswith("municipal-pdf-"))

    def test_double_visual_integrity_for_santa_lucia(self):
        first=dict(EVENT)
        second={**first,"evidence":"30 octubre 21:00 Concierto de música popular en Recinto Ferial de Vecindario"}
        approved=verified.approved_candidates([first],[second],today=DAY)
        self.assertEqual(len(approved),1)
        record,error=vision.validate_candidate(approved[0],2026,"San Rafael",
                                     URL,SHA,0,DAY,municipality=ST)
        self.assertIsNone(error)
        record["review_status"]="auto_verified"
        record["verification"]="two_independent_visual_passes"
        key=f"{SHA}/0/{vision.MODEL}/{auto.VERSION}"
        cache={
            key+"/ai_vision":{"output":{"events":[first],"page_is_program":True}},
            key+"/independent_double_read":{"output":{"events":[second],"page_is_program":True}}
        }
        state={hashlib.sha256(URL.encode()).hexdigest()[:16]:
               {"sha":SHA,"done_pages":[0]}}
        self.assertTrue(integrity.trusted(record,{URL},state,cache,DAY,
                                         vision.MODEL,auto.VERSION))
        item=verified.approved_to_event(record)
        self.assertEqual(item["municipality"],ST)
        self.assertIn(ST,item["source_name"])
        self.assertEqual(item["source_url"],URL)
        self.assertIsNone(item["free"])
        self.assertFalse(integrity.trusted(record,{URL},{},cache,DAY,
                                          vision.MODEL,auto.VERSION))

    def test_state_and_queue_empty_on_archive_only_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)
            index=t/"index.json"
            index.write_text(json.dumps(sources.build_catalog(2026,FakeHttp("<main></main>"))),
                             encoding="utf8")
            changes={auto.INDEX:index,auto.STATE:t/"state.json",auto.REVIEW:t/"pending.json",
                     auto.VERIFIED:t/"verified.json",auto.ARCHIVE:t/"archive.json",
                     auto.CACHE:t/"cache.json",auto.REPORT:t/"report.json"}
            from contextlib import ExitStack
            with ExitStack() as stack:
                for attribute,file in (("INDEX",index),("STATE",t/"state.json"),
                    ("REVIEW",t/"pending.json"),("VERIFIED",t/"verified.json"),
                    ("ARCHIVE",t/"archive.json"),("CACHE",t/"cache.json"),
                    ("REPORT",t/"report.json")):
                    stack.enter_context(patch.object(auto,attribute,file))
                with patch.object(sources,"robots_for",side_effect=AssertionError("network!")):
                    report=auto.run(["--archive-only"],today=DAY)
            self.assertEqual(report["api_calls"],0)
            self.assertEqual(report["documents"],[])
            self.assertEqual(json.loads((t/"pending.json").read_text()),[])

    def test_page_selection_prefers_future_schedule_sections(self):
        class Page:
            def __init__(self,t):self.t=t
            def extract_text(self):return self.t
        class Doc:
            pages=[Page("Saluda del Alcalde"),Page("MARTES 27 DE OCTUBRE 18:00 h. Actuación"),
                   Page("MIÉRCOLES 30 DE SEPTIEMBRE 18:00 h. Teatro"),
                   Page("VIERNES 30 DE OCTUBRE 21:30 h. Verbena")]
        result=auto.page_scores(Doc(),2026,DAY)
        self.assertEqual([x[0] for x in result[:2]],[1,3])

if __name__=="__main__":
    unittest.main()
