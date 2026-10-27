import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import gc_source_radar as radar

class RadarTests(unittest.TestCase):
    def test_official_host_no_external_or_credentials(self):
        home="https://www.villadefirgas.es/"
        self.assertTrue(radar.same_official_host("https://villadefirgas.es/agenda",home))
        self.assertFalse(radar.same_official_host("https://www.villadefirgas.es.evil.com/agenda",home))
        self.assertFalse(radar.same_official_host("http://villadefirgas.es/agenda",home))
        self.assertFalse(radar.same_official_host("https://user@villadefirgas.es/agenda",home))

    def test_candidates_are_never_event_records(self):
        body=b"""<html><a href="/cultura/fiestas-patronales/">Programa de fiestas patronales 2026</a>
             <a href="https://evil.example/programa-fiesta">Concierto para todas las edades</a>
             <a href="/politica-privacidad">Aviso legal</a></html>"""
        links=radar.candidate_links("https://www.villadefirgas.es/",body)
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["kind"],"unverified_official_link")
        self.assertNotIn("start",links[0])
        self.assertNotIn("status",links[0])

    def test_404_robots_allowed_403_fail_closed(self):
        class FakeResponse:
            def __init__(self,status):
                self.status_code=status
                self.text=""
        class FakeSession:
            def __init__(self,status):self.status=status
            def get(self,*a,**kw):return FakeResponse(self.status)
        radar.allowed(FakeSession(404),"https://www.villadefirgas.es")
        with self.assertRaises(RuntimeError):
            radar.allowed(FakeSession(403),"https://www.villadefirgas.es")

    def test_budget_and_state_allow_incremental_scan(self):
        class FakeSession:pass
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"lead.json"
            catalog={"municipalities":[
                {"municipality":"Agaete","status":"conector_parcial","official_website":"https://agaete.es/"},
                {"municipality":"Tejeda","status":"conector_activo","official_website":"https://tejeda.eu/"},
                {"municipality":"Firgas","status":"sin_conector","official_website":"https://villadefirgas.es/"}]}
            with patch.object(radar,"OUTPUT",target),patch.object(radar,"inspect",return_value=[
                 {"url":"https://agaete.es/evento/fiestas","label":"Fiestas Agaete","kind":"unverified_official_link"}
            ]) as inspect:
                out=radar.run(["--max-sites","1"],today=dt.date(2026,10,27),
                              session=FakeSession(),registry=catalog)
                self.assertEqual(inspect.call_count,1)
                self.assertTrue(out["no_auto_publication"])
                self.assertEqual(len(out["leads"]),1)
                self.assertEqual(out["leads"][0]["publication_status"],"not_an_event")
                out2=radar.run(["--max-sites","1"],today=dt.date(2026,10,28),
                               session=FakeSession(),registry=catalog)
                self.assertEqual(out2["inspected"][0]["municipality"],"Firgas")

if __name__=="__main__":
    unittest.main()
