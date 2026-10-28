"""Visual reading cannot invent a place from an event title alone."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.robotparser import RobotFileParser

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import poster_venues as p

MOGAN_URL="https://www.eventosgrancanaria.com/event/E-20261031-0013/noche-de-finaos"
MOGAN_IMAGE=p.MANUALLY_VERIFIED[MOGAN_URL]["poster_image_url"]
MOGAN_SHA=p.MANUALLY_VERIFIED[MOGAN_URL]["poster_sha256"]
DATE=dt.date(2026,10,27)
DATE2=dt.date(2026,11,2)

def setup():
    con=sqlite3.connect(":memory:")
    con.row_factory=sqlite3.Row
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY,title TEXT,start TEXT,end TEXT,municipality TEXT,venue TEXT,image_url TEXT,source_url TEXT,status TEXT,updated_at TEXT)")
    con.execute("INSERT INTO events VALUES (119,?,?,?,?,?,?,?,'approved',NULL)",(
        "Noche de Finaos","2026-10-31T19:00:00",None,"Mogán",
        "Consultar el recinto en la ficha oficial",MOGAN_IMAGE,MOGAN_URL))
    return con

class PosterVerificationTests(unittest.TestCase):
    def test_urls_whitelisted_no_external_or_credentials(self):
        self.assertTrue(p.allowed_event(MOGAN_URL))
        self.assertTrue(p.allowed_image(MOGAN_IMAGE))
        self.assertFalse(p.allowed_image("https://www.eventosgrancanaria.com.evil.net/controlpanel/files/gridfs/6ad718cb013a6268e07a7c2a"))
        self.assertFalse(p.allowed_image("https://a@www.eventosgrancanaria.com/controlpanel/files/gridfs/6ad718cb013a6268e07a7c2a"))
        self.assertFalse(p.allowed_image("http://www.eventosgrancanaria.com/controlpanel/files/gridfs/6ad718cb013a6268e07a7c2a"))
        self.assertFalse(p.allowed_image(MOGAN_IMAGE+"?raw=true"))
        self.assertFalse(p.allowed_event(MOGAN_URL+"?redirect=http://evil.example"))

    def test_manual_user_proof_requires_unchanged_exact_official_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/"reviewed.json"
            report=Path(tmp)/"report.json"
            policy=RobotFileParser();policy.allow_all=True
            conn=setup()
            with patch.object(p,"CACHE",cache),patch.object(p,"REPORT",report),patch.object(p,"source_policy",return_value=policy),patch.object(p,"download_poster",return_value=(MOGAN_SHA,b"jpeg")):
                result=p.enrich(conn,DATE.isoformat(),DATE,api_key="",max_posters=1)
            self.assertEqual(result["manual_verified"],1)
            self.assertEqual(result["api_calls"],0)
            self.assertEqual(conn.execute("SELECT venue FROM events WHERE id=119").fetchone()[0],"Parque Nicolás Quesada")
            rows=json.loads(cache.read_text(encoding="utf8"))["posters"]
            self.assertEqual(rows[MOGAN_URL]["sha256"],MOGAN_SHA)
            self.assertNotIn("jpeg",cache.read_text(encoding="utf8"))
            self.assertEqual(rows[MOGAN_URL]["method"],"human_posted_poster")

            # Same title/date but the official JPEG changed. Do not trust
            # what a previous human saw in the earlier image.
            other=setup()
            with patch.object(p,"CACHE",Path(tmp)/"different.json"),patch.object(p,"REPORT",report),patch.object(p,"source_policy",return_value=policy),patch.object(p,"download_poster",return_value=("0"*64,b"other")):
                result=p.enrich(other,DATE.isoformat(),DATE,api_key="",max_posters=1)
            self.assertEqual(result["manual_verified"],0)
            self.assertIn("Consultar el recinto",other.execute("SELECT venue FROM events WHERE id=119").fetchone()[0])

    def test_refuse_wrong_day_title_or_conflicting_venues(self):
        event={"title":"Noche de Finaos","start":"2026-10-31T19:00:00","municipality":"Mogán"}
        first={"one_event_single_venue":True,"poster_title":"Noche de Finaos Mogán",
               "date_text":"Día 31 de octubre","venue":"Parque Nicolás Quesada",
               "venue_evidence":"EN EL PARQUE NICOLÁS QUESADA"}
        self.assertEqual(p.check_reading(first,event),"Parque Nicolás Quesada")
        self.assertEqual(p.agreement(first,dict(first),event),"Parque Nicolás Quesada")
        self.assertFalse(p.agreement(first,{**first,"venue":"Parque del Sur",
                                       "venue_evidence":"Parque del Sur"},event))
        self.assertFalse(p.agreement(first,{**first,"date_text":"30 de octubre"},event))
        self.assertFalse(p.agreement(first,{**first,"poster_title":"Otro evento"},event))
        self.assertFalse(p.agreement(first,{**first,"venue":"Mogán",
                                       "venue_evidence":"Mogán"},event))
        self.assertFalse(p.agreement(first,{**first,"venue":"Parque Nicolás Quesada",
                                       "venue_evidence":""},event))
        self.assertFalse(p.agreement(first,{**first,"one_event_single_venue":False},event))

    def test_api_calls_require_second_read_and_appear_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup()
            cache=Path(tmp)/"reviewed.json"
            report=Path(tmp)/"report.json"
            policy=RobotFileParser();policy.allow_all=True
            obj={"one_event_single_venue":True,"poster_title":"Noche de Finaos",
                 "date_text":"31 de octubre","venue":"Parque Nicolás Quesada",
                 "venue_evidence":"Parque Nicolás Quesada"}
            with patch.object(p,"CACHE",cache),patch.object(p,"REPORT",report),patch.object(p,"source_policy",return_value=policy),patch.object(p,"download_poster",return_value=("0"*64,b"jpeg")),patch.object(p,"vision_call",return_value=(obj,{"input_tokens":600,"output_tokens":100})) as model:
                out=p.enrich(c,DATE.isoformat(),DATE,api_key="test-only-key",max_posters=1)
            self.assertEqual(out["manual_verified"],0)
            self.assertEqual(out["vision_verified"],1)
            self.assertEqual(out["api_calls"],2)
            self.assertEqual(model.call_count,2)
            self.assertEqual(c.execute("SELECT venue FROM events WHERE id=119").fetchone()[0],"Parque Nicolás Quesada")
            state=json.loads(cache.read_text(encoding="utf8"))["posters"][MOGAN_URL]
            self.assertEqual(state["method"],"two_independent_visual_passes")

    def test_no_key_means_no_ai_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup()
            policy=RobotFileParser();policy.allow_all=True
            with patch.object(p,"CACHE",Path(tmp)/"reviewed.json"),patch.object(p,"REPORT",Path(tmp)/"report.json"),patch.object(p,"source_policy",return_value=policy),patch.object(p,"download_poster",return_value=("0"*64,b"poster")):
                result=p.enrich(c,DATE.isoformat(),DATE,api_key="",max_posters=1)
            self.assertEqual(result["api_calls"],0)
            self.assertEqual(result["vision_verified"],0)
            self.assertEqual(result["manual_verified"],0)

if __name__=="__main__":
    unittest.main()
