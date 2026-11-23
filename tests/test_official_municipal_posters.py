"""Regression: verified Guía and Vega event images remain attached in the catalog."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import official_municipal_posters as posters


GUIA_IMAGE = (
    "https://santamariadeguia.es/wp-content/uploads/2026/11/"
    "WhatsApp-Image-2026-11-20-at-14.19.48.jpeg"
)
VEGA_IMAGE = "https://www.vegadesanmateo.es/sites/default/files/noticias/Cartel.jpg"
GUIA_HTML = (
    '<meta property="og:image" content="' + GUIA_IMAGE + '">'
    "<article><h1>Guía celebra el encendido de Navidad y La Trova</h1></article>"
)
VEGA_HTML = (
    '<article><h1>III Mercado Navideño de Vega de San Mateo</h1>'
    '<a href="' + VEGA_IMAGE + '"><img alt="Cartel III Mercado Navideño 2026" '
    'src="/sites/default/files/styles/max_650x650/public/noticias/Cartel.jpg">'
    "</a></article>"
)


class MunicipalOfficialPostersTests(unittest.TestCase):
    def test_guia_news_og_image_verified_by_exact_article_and_host(self):
        r = posters.from_official_article(
            BeautifulSoup(GUIA_HTML, "html.parser"), posters.GUIA_URL)
        self.assertEqual(r["image_url"], GUIA_IMAGE)
        self.assertEqual(r["image_status"], "official_remote")
        self.assertEqual(r["image_origin"], posters.GUIA_URL)
        self.assertIn("Guía", r["image_alt"])
        self.assertEqual(posters.from_official_article(
            BeautifulSoup(GUIA_HTML, "html.parser"),
            "https://santamariadeguia.es/otra-noticia/"), {})
        unsafe = GUIA_HTML.replace("santamariadeguia.es", "example.org")
        self.assertEqual(posters.from_official_article(
            BeautifulSoup(unsafe, "html.parser"), posters.GUIA_URL), {})
        old = GUIA_HTML.replace("/2026/11/", "/2025/11/")
        self.assertEqual(posters.from_official_article(
            BeautifulSoup(old, "html.parser"), posters.GUIA_URL), {})

    def test_vega_poster_requires_matching_alt_and_full_source_link(self):
        r = posters.from_official_article(
            BeautifulSoup(VEGA_HTML, "html.parser"), posters.VEGA_URL)
        self.assertEqual(r["image_url"], VEGA_IMAGE)
        self.assertIn("III Mercado", r["image_alt"])
        replaced = VEGA_HTML.replace("Cartel III Mercado Navideño 2026",
                                     "Logotipo genérico del Ayuntamiento")
        self.assertEqual(posters.from_official_article(
            BeautifulSoup(replaced, "html.parser"), posters.VEGA_URL), {})
        missing_link = VEGA_HTML.replace('<a href="' + VEGA_IMAGE + '">',
                                         '<a href="https://untrusted.example/poster.jpg">')
        self.assertEqual(posters.from_official_article(
            BeautifulSoup(missing_link, "html.parser"), posters.VEGA_URL), {})

    def database(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE events (
            id INTEGER PRIMARY KEY,source_url TEXT,status TEXT,
            start TEXT,"end" TEXT,image_url TEXT,image_alt TEXT,
            image_origin TEXT,image_status TEXT,updated_at TEXT)""")
        for event_id, url, existing in [
            (998, posters.GUIA_URL, ""),
            (617, posters.VEGA_URL, ""),
            (618, posters.VEGA_URL, ""),
            (619, posters.VEGA_URL, ""),
            (620, posters.VEGA_URL, "https://approved.example/existing.jpg"),
            (777, "https://another.example/other", ""),
        ]:
            conn.execute(
                'INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',
                (event_id, url, "approved", "2026-11-27", None,
                 existing, "", "", "", "2026-11-01"))
        return conn

    def test_repairs_four_records_and_does_not_touch_approved_images(self):
        conn = self.database()
        downloaded = []
        def fetch(url):
            downloaded.append(url)
            return BeautifulSoup(
                GUIA_HTML if url == posters.GUIA_URL else VEGA_HTML,
                "html.parser")
        result = posters.backfill_approved_missing(
            conn, "2026-11-23T18:00:00", dt.date(2026,11,23), fetch)
        self.assertEqual(result["changed"], 4)
        self.assertEqual(result["found"], 2)
        self.assertEqual(len(downloaded), 2)
        got = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events")}
        self.assertEqual(got[998]["image_url"], GUIA_IMAGE)
        for i in (617,618,619):
            self.assertEqual(got[i]["image_url"], VEGA_IMAGE)
            self.assertEqual(got[i]["image_status"], "official_remote")
        self.assertEqual(got[620]["image_url"],
                         "https://approved.example/existing.jpg")
        self.assertEqual(got[777]["image_url"], "")
        again = posters.backfill_approved_missing(
            conn, "2026-11-23T19:00:00", dt.date(2026,11,23), fetch)
        self.assertEqual(again["changed"], 0)
        self.assertEqual(len(downloaded), 2)
        conn.close()

    def test_failed_source_is_isolated_and_untouched(self):
        conn=self.database()
        def fetch(url):
            if url == posters.GUIA_URL: raise PermissionError("blocked")
            return BeautifulSoup(VEGA_HTML, "html.parser")
        report=posters.backfill_approved_missing(
            conn,"2026-11-23T18:00:00",dt.date(2026,11,23),fetch)
        self.assertEqual(report["changed"],3)
        self.assertIn("PermissionError",report["error"])
        self.assertEqual(conn.execute("SELECT image_url FROM events WHERE id=998").fetchone()[0],"")
        conn.close()


    def test_guia_discovery_extractor_passes_official_image_into_event(self):
        from municipal_live_discovery import parse_guia_article
        html = '<meta property="og:image" content="' + GUIA_IMAGE + '">' + """<article>
            <time datetime="2026-11-20T15:00:00+00:00"></time>
            <div class="entry-content">Guía celebrará el 26 de noviembre
              su encendido de Navidad con La Trova.
              El concierto se celebrará en la Iglesia de Santa María de Guía
              y dará comienzo a las 20:30 horas.</div>
            </article>"""
        # An exact article is necessary: the source parser can reject
        # ambiguous schedules without ever attaching its artwork.
        event = parse_guia_article(
            BeautifulSoup(html, "html.parser"),
            "Guía dará la bienvenida a la Navidad con el concierto de La Trova",
            posters.GUIA_URL, dt.date(2026, 11, 23), lambda _: "musica")
        self.assertIsNotNone(event)
        self.assertEqual(event["image_url"], GUIA_IMAGE)
        self.assertEqual(event["image_status"], "official_remote")

    def test_vega_documented_extractor_passes_original_poster(self):
        from gc_documented_events import extract
        spec = {"municipality": "Vega de San Mateo",
                "url": posters.VEGA_URL,
                "events": [{
                    "title": "III Mercado Navideño de Vega de San Mateo",
                    "date": "2026-11-27", "time": "16:00",
                    "venue": "Rambla de la Constitución",
                    "category": "gastronomia",
                    "tokens": ("27 de noviembre de 2026", "mercado navideño"),
                    "details": "Mercado navideño de Vega de San Mateo."
                }]}
        html = VEGA_HTML.replace("</article>",
            "<p>27 de noviembre de 2026; mercado navideño.</p></article>")
        entries, audit = extract(
            lambda _: BeautifulSoup(html, "html.parser"),
            dt.date(2026, 11, 23), {"Vega de San Mateo": (28.01, -15.53)},
            source_specs=(spec,))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["image_url"], VEGA_IMAGE)
        self.assertEqual(entries[0]["image_status"], "official_remote")
        self.assertEqual(audit[0]["status"], "checked")


if __name__ == "__main__":
    unittest.main()
