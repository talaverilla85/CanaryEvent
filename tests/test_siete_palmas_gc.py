"""Siete Palmas news: fail closed until an actual future activity is dated."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shopping_centres_gc as malls

FEED = """
<main><h1>Más experiencias</h1>
<a href="/ahora-mas/eventos/en-esta-casa-la-navidad-empieza-contigo">Navidad</a>
<a href="/ahora-mas/eventos/taller-familiar-de-diciembre">Taller</a>
<a href="https://other.example/ahora-mas/eventos/wrong">External</a>
<a href="/ahora-mas/articulos/ofertas-navidenas">Retail article</a>
<a href="/ahora-mas/eventos/taller-familiar-de-diciembre">Repeated card</a>
</main>
"""
OLD = """
<main><h1>En esta casa, la Navidad empieza contigo</h1>
<p>Fecha 17 de noviembre 2026</p>
<p>El viernes 20 de noviembre encendemos las luces.</p>
<p>Te esperamos el 20 de noviembre, de 18:00 a 20:00 horas, en la Planta 1.</p>
</main>
"""
UPCOMING = """
<main><h1>Taller familiar de Navidad</h1>
<p>Fecha 24 de noviembre 2026</p>
<p>El jueves 26 de noviembre, de 17:00 a 20:00 horas, hay un taller familiar.</p>
</main>
"""


class SietePalmasTests(unittest.TestCase):
    def source(self, slug="taller-familiar-de-diciembre"):
        return "https://sietepalmascc.com/ahora-mas/eventos/" + slug

    def extract(self, html=UPCOMING, day=dt.date(2026, 11, 24)):
        return malls.extract_siete_palmas_article(
            BeautifulSoup(html, "html.parser"), self.source(), day)

    def test_only_same_site_article_urls_and_deduplicated_feed(self):
        self.assertEqual(malls.siete_palmas_links(BeautifulSoup(FEED, "html.parser")),
                         [self.source("en-esta-casa-la-navidad-empieza-contigo"),
                          self.source()])

    def test_verified_future_programme_with_date_time_source_and_no_image(self):
        entry = self.extract()
        self.assertIsNotNone(entry)
        self.assertEqual(entry["start"], "2026-11-26T17:00:00")
        self.assertEqual(entry["end"], "2026-11-26T20:00:00")
        self.assertEqual(entry["venue"], "Centro Comercial Siete Palmas")
        self.assertEqual(entry["source_name"], malls.SP_NAME)
        self.assertEqual(entry["source_url"], self.source())
        self.assertEqual(entry["category"], "familia")
        self.assertIsNone(entry["free"])
        self.assertEqual(entry["image_url"], "")
        self.assertIn("26/11/2026", entry["details"])

    def test_actual_november_20_article_is_past_not_republished(self):
        self.assertIsNone(self.extract(OLD))

    def test_reject_old_article_copied_into_2026_and_weekday_mismatch(self):
        self.assertIsNone(self.extract(
            UPCOMING.replace("24 de noviembre 2026", "24 de noviembre 2025")))
        self.assertIsNone(self.extract(
            UPCOMING.replace("jueves 26", "viernes 26")))

    def test_no_automatic_guess_from_marketing_content(self):
        no_hour = UPCOMING.replace("de 17:00 a 20:00 horas", "por la tarde")
        self.assertIsNone(self.extract(no_hour))
        retail = UPCOMING.replace("Taller familiar de Navidad",
                                  "Ofertas Black Friday de Navidad")
        self.assertIsNone(self.extract(retail))
        multiple_dates = UPCOMING.replace(
            "El jueves 26 de noviembre,",
            "El jueves 26 de noviembre y viernes 27 de noviembre,")
        self.assertIsNone(self.extract(multiple_dates))

    def test_fully_dated_event_without_article_date_is_allowed(self):
        html = """<main><h1>Concierto de Navidad</h1>
        <p>El jueves 26 de noviembre de 2026 a las 19:00 horas.</p></main>"""
        event = self.extract(html)
        self.assertIsNotNone(event)
        self.assertEqual(event["start"], "2026-11-26T19:00:00")
        self.assertIsNone(event["end"])

    def test_stale_headline_without_event_date_is_rejected(self):
        html = """<main><h1>Navidad, un plan en familia</h1>
        <p>Fecha 17 de noviembre 2026</p>
        <p>Descubre la nueva casa de Papá Noel, cada día más cerca.</p></main>"""
        self.assertIsNone(self.extract(html))

    def test_daily_sync_is_isolated_idempotent_and_tracks_zero_events(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE source_log(
            source TEXT PRIMARY KEY, checked_at TEXT, found INTEGER,
            added INTEGER, changed INTEGER, error TEXT)""")
        stored = {}
        def upsert(_conn, item):
            key = (item["source_url"], item["start"])
            existed = key in stored
            stored[key] = item
            return "unchanged" if existed else "added"
        def fetch(url):
            if url == malls.SP_URL:
                return BeautifulSoup(FEED, "html.parser")
            if url == self.source("en-esta-casa-la-navidad-empieza-contigo"):
                return BeautifulSoup(OLD, "html.parser")
            if url == self.source():
                return BeautifulSoup(UPCOMING, "html.parser")
            raise AssertionError("Unexpected URL")
        first = malls.synchronize_siete_palmas(
            conn, "2026-11-24T08:00:00", dt.date(2026, 11, 24), upsert, fetch)
        self.assertEqual(first["found"], 1)
        self.assertEqual(first["added"], 1)
        self.assertEqual(first["error"], "")
        self.assertEqual(first["articles_checked"], 2)
        later = malls.synchronize_siete_palmas(
            conn, "2026-11-24T10:00:00", dt.date(2026, 11, 24), upsert, fetch)
        self.assertEqual(later["added"], 0)
        self.assertEqual(later["found"], 1)
        no_future = malls.synchronize_siete_palmas(
            conn, "2026-12-31T10:00:00", dt.date(2026, 12, 31), upsert, fetch)
        self.assertEqual(no_future["found"], 0)
        self.assertEqual(no_future["error"], "")
        self.assertEqual(len(stored), 1)
        conn.close()

    def test_blocked_listing_records_error_without_interrupting_sync(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE source_log(
            source TEXT PRIMARY KEY, checked_at TEXT, found INTEGER,
            added INTEGER, changed INTEGER, error TEXT)""")
        def fail(_):
            raise PermissionError("robots disallows")
        result = malls.synchronize_siete_palmas(
            conn, "2026-11-24T08:00:00", dt.date(2026, 11, 24),
            lambda *_: None, fail)
        self.assertEqual(result["found"], 0)
        self.assertIn("PermissionError", result["error"])
        self.assertIn("PermissionError",
                      conn.execute("SELECT error FROM source_log").fetchone()[0])
        conn.close()


if __name__ == "__main__":
    unittest.main()
