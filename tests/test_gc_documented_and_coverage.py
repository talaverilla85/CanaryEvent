import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import gc_documented_events as verified
import coverage_gc
import sync_events

class FactCheckedMunicipalSourcesTests(unittest.TestCase):
    def test_official_sources_only_and_no_invented_prices(self):
        self.assertEqual(len(verified.SOURCES),5)
        self.assertEqual(sum(len(x["events"]) for x in verified.SOURCES),12)
        for source in verified.SOURCES:
            self.assertTrue(source["url"].startswith("https://"))
            for event in source["events"]:
                self.assertIsNone(event.get("free"))
                self.assertIsNone(event.get("price"))
                self.assertTrue(event["venue"])
                self.assertEqual(len(event["time"]),5)

    def test_rechecked_article_does_not_publish_if_evidence_changes(self):
        sample=verified.SOURCES[0]
        item=sample["events"][0]
        soup=BeautifulSoup("<article>El colegio del Terror 30 31 octubre Parque Popular, sin horario</article>",
                           "html.parser")
        self.assertFalse(verified.verify_article(item,soup))
        rows,report=verified.extract(lambda _:soup,dt.date(2026,10,27),{"Agaete":(28,-15)},
                                     source_specs=(sample,))
        self.assertEqual(rows,[])
        self.assertEqual(report[0]["status"],"unverified_text")

    def test_past_2026_acts_never_republished(self):
        def no_fetch(_):raise AssertionError("Historical article should not be downloaded")
        records,audit=verified.extract(no_fetch,dt.date(2026,12,2),
                    {source["municipality"]:(28,-15) for source in verified.SOURCES})
        self.assertEqual(records,[])
        self.assertEqual(audit,[])

    def test_404_robots_file_is_not_disallow(self):
        class Reply:
            status_code=404
        with patch.object(sync_events.requests,"get",return_value=Reply()) as request:
            self.assertIsNone(sync_events.allowed("https://www.maspalomas.com/mnunotjuventud/test"))
            self.assertEqual(request.call_count,1)
        class Forbidden:
            status_code=403
        with patch.object(sync_events.requests,"get",return_value=Forbidden()):
            with self.assertRaises(RuntimeError):
                sync_events.allowed("https://www.maspalomas.com/mnunotjuventud/test")

    def test_21_municipality_matrix_distinguishes_official_and_other_sources(self):
        source=coverage_gc.read(coverage_gc.SRC,{})
        self.assertEqual(len(source["municipalities"]),21)
        events={"events":[
            {"title":"Feria","municipality":"Agaete","source_name":"Ayuntamiento de Agaete · actos documentados"},
            {"title":"Otro evento","municipality":"Vega de San Mateo","source_name":"Entradas comerciales"},
        ]}
        report=coverage_gc.make_report(registry=source,metadata={"sources":[]},catalog=events,
                                      today=dt.date(2026,10,27))
        self.assertEqual(report["municipalities_total"],21)
        self.assertFalse(report["full_coverage_confirmed"])
        item={x["municipality"]:x for x in report["municipalities"]}
        self.assertEqual(item["Agaete"]["municipal_cards_total"],1)
        self.assertEqual(item["Vega de San Mateo"]["municipal_cards_total"],0)
        self.assertEqual(item["Vega de San Mateo"]["other_sources_cards_total"],1)
        self.assertFalse(item["Agaete"]["full_coverage_claim"])

if __name__=="__main__":unittest.main()
