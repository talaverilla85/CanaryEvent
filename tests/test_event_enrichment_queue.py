"""Regression tests for unattended incremental enrichment and proof preservation."""
import json
import sqlite3
import sys
import unittest
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import event_enrichment as mod
import verified_venue_coordinates as places

DESCRIPTION = (
    "Un concierto especial para disfrutar de las voces y los instrumentos "
    "de la música antigua. El programa presenta varias composiciones "
    "interpretadas por artistas invitados en el teatro municipal de Ingenio."
)
BASE = {
    "id": 101, "status": "approved", "title": "La noche de las artes",
    "start": "2026-12-05", "end": None, "municipality": "Ingenio",
    "venue": "Lugar por confirmar", "accuracy": "municipality",
    "lat": 27.91, "lng": -15.43, "details": "",
    "source_url": "https://ingenio.es/events/las-artes/",
    "organizer_url": "", "image_url": "", "image_status": "",
    "price": "", "free": None, "updated_at": "2026-11-21T00:00:00",
}
COLUMNS = tuple(BASE)


def db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE events (
        id INTEGER PRIMARY KEY, status TEXT, title TEXT, start TEXT, "end" TEXT,
        municipality TEXT, venue TEXT, accuracy TEXT, lat REAL, lng REAL,
        details TEXT, source_url TEXT, organizer_url TEXT, image_url TEXT,
        image_status TEXT, price TEXT, free INTEGER, updated_at TEXT)""")
    return c


def put(c, **kwargs):
    row = {**BASE, **kwargs}
    c.execute(
        "INSERT INTO events (" + ",".join('"' + k + '"' for k in COLUMNS)
        + ") VALUES (" + ",".join("?" for _ in COLUMNS) + ")",
        tuple(row[k] for k in COLUMNS),
    )


def soup(**kwargs):
    event = {
        "@context": "https://schema.org", "@type": "Event",
        "name": "La noche de las artes", "startDate": "2026-12-05T20:00:00+00:00",
        "description": DESCRIPTION,
        "location": {
            "@type": "Place", "name": "Teatro de la Villa",
            "address": {"addressLocality": "Ingenio"},
            "geo": {"@type": "GeoCoordinates", "latitude": 27.9201, "longitude": -15.4452},
        },
        "offers": {"@type": "Offer", "price": "12.50", "priceCurrency": "EUR"},
        "image": "https://ingenio.es/uploads/cartel.jpg",
    }
    event.update(kwargs)
    return BeautifulSoup(
        '<script type="application/ld+json">' + json.dumps(event) + "</script>",
        "html.parser",
    )


class QueueTests(unittest.TestCase):
    def test_new_events_are_served_across_daily_runs_without_starving(self):
        c = db()
        for i in range(101, 110):
            put(c, id=i, source_url="https://ingenio.es/events/" + str(i))
        calls = []
        def fetch(url):
            calls.append(url)
            return soup(name="Otro evento")
        for day, expected in [(22, 3), (23, 6), (24, 9)]:
            result = mod.enrich(c, f"2026-11-{day}T08:00:00", date(2026, 11, day),
                                fetch_html=fetch, max_requests=3, max_events=3)
            self.assertEqual(result["requests"], 3)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM event_enrichment_checks").fetchone()[0], expected)
        self.assertEqual(len(set(calls)), 9)
        self.assertEqual(len(calls), 9)
        c.close()

    def test_no_retries_until_due_and_exponential_backoff(self):
        c = db()
        put(c)
        fetch = lambda url: soup(name="Otro evento")
        first = mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22), fetch_html=fetch)
        self.assertEqual(first["requests"], 1)
        early = mod.enrich(c, "2026-11-23T08:00:00", date(2026, 11, 23), fetch_html=fetch)
        self.assertEqual(early["requests"], 0)
        due = mod.enrich(c, "2026-11-25T08:00:00", date(2026, 11, 25), fetch_html=fetch)
        self.assertEqual(due["requests"], 1)
        check = c.execute("SELECT attempts,next_check_at FROM event_enrichment_checks").fetchone()
        self.assertEqual(check["attempts"], 2)
        self.assertTrue(check["next_check_at"].startswith("2026-12-01"))
        c.close()

    def test_official_event_fills_seo_gaps_price_poster_geo(self):
        c = db()
        put(c)
        result = mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22),
                            fetch_html=lambda url: soup())
        self.assertEqual(result["verified"], 1)
        self.assertEqual(result["newly_eligible"], 1)
        self.assertEqual(result["requests"], 1)
        row = dict(c.execute("SELECT * FROM events").fetchone())
        self.assertEqual(row["start"], "2026-12-05T20:00:00")
        self.assertEqual(row["venue"], "Teatro de la Villa")
        self.assertEqual(row["accuracy"], "venue")
        self.assertAlmostEqual(row["lat"], 27.9201)
        self.assertEqual(row["free"], 0)
        self.assertEqual(row["price"], "12,5 €")
        self.assertEqual(row["image_status"], "official_remote")
        self.assertEqual(row["image_url"], "https://ingenio.es/uploads/cartel.jpg")
        self.assertTrue(mod.meaningful_description(row["details"]))
        self.assertTrue(mod.seo_ready(row))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM event_enrichment_proofs").fetchone()[0], 11)
        c.close()

    def test_verified_facts_survive_next_source_refresh_without_network(self):
        c = db()
        put(c)
        mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22),
                   fetch_html=lambda url: soup())
        # Simulate the original source-specific parser publishing a thinner card.
        c.execute("""UPDATE events SET start='2026-12-05',venue='Lugar por confirmar',
                     accuracy='municipality',lat=27.91,lng=-15.43,details='',
                     price='',free=NULL,image_url='',image_status='' WHERE id=101""")
        def no_network(_):
            raise AssertionError("The verified proof must be reused")
        result = mod.enrich(c, "2026-11-23T08:00:00", date(2026, 11, 23),
                            fetch_html=no_network)
        self.assertEqual(result["requests"], 0)
        self.assertEqual(result["restored"], 1)
        row = dict(c.execute("SELECT * FROM events").fetchone())
        self.assertTrue(mod.seo_ready(row))
        self.assertEqual(row["accuracy"], "venue")
        self.assertEqual(row["free"], 0)
        self.assertEqual(row["start"], "2026-12-05T20:00:00")
        self.assertEqual(row["image_status"], "official_remote")
        self.assertEqual(
            places.backfill(c, {"Ingenio": (27.91, -15.43)}), 0,
            "Official event-specific geometry must survive the existing backfill",
        )
        c.close()

    def test_never_reapply_proof_to_changed_title_date_or_source(self):
        c = db()
        put(c)
        mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22),
                   fetch_html=lambda url: soup())
        c.execute("""UPDATE events SET title='Un evento distinto',
                     details='',venue='Lugar por confirmar',
                     start='2026-12-05',accuracy='municipality' WHERE id=101""")
        result = mod.enrich(c, "2026-11-23T08:00:00", date(2026, 11, 23),
                            fetch_html=lambda url: soup(name="Otro evento"))
        self.assertEqual(result["restored"], 0)
        row = c.execute("SELECT details,venue FROM events").fetchone()
        self.assertEqual(row["details"], "")
        self.assertEqual(row["venue"], "Lugar por confirmar")
        c.close()

    def test_mismatched_city_cannot_verify_coordinates_or_venue(self):
        event = {**BASE}
        bad = soup(location={
            "@type": "Place", "name": "Teatro de la Villa",
            "address": {"addressLocality": "Telde"},
            "geo": {"latitude": 27.9201, "longitude": -15.4452},
        })
        self.assertEqual(mod.structured_evidence(event, bad), {})

    def test_ambiguous_same_day_schema_is_not_accepted(self):
        raw = str(soup())
        two = BeautifulSoup(raw + raw, "html.parser")
        self.assertEqual(mod.structured_evidence(BASE, two), {})

    def test_external_image_and_unproven_offers_rejected(self):
        result = mod.structured_evidence(BASE, soup(
            image="https://bad.example/cartel.jpg",
            offers={"price": "9.99"},
        ))
        self.assertNotIn("image_url", result)
        self.assertNotIn("price", result)
        self.assertNotIn("free", result)

    def test_detail_discovery_only_exact_match_on_same_official_site(self):
        c = db()
        put(c)
        called = []
        source = BASE["source_url"]
        detail = "https://ingenio.es/events/la-noche-de-las-artes/"
        listing = BeautifulSoup(
            '<a href="/events/la-noche-de-las-artes/">La noche de las artes</a>'
            '<a href="https://bad.example/post">La noche de las artes</a>', "html.parser")
        def fetch(url):
            called.append(url)
            return listing if url == source else soup()
        result = mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22),
                            fetch_html=fetch, max_requests=2)
        self.assertEqual(result["verified"], 1)
        self.assertEqual(called, [source, detail])
        c.close()

    def test_untrusted_source_creates_audited_retry_without_fetch(self):
        c = db()
        put(c, source_url="https://untrusted.example/events/abc")
        r = mod.enrich(c, "2026-11-22T08:00:00", date(2026, 11, 22),
                       fetch_html=lambda url: self.fail("Should not fetch"))
        self.assertEqual(r["requests"], 0)
        self.assertEqual(r["checked"], 1)
        check = c.execute("SELECT outcome,next_check_at FROM event_enrichment_checks").fetchone()
        self.assertEqual(check["outcome"], "no_eligible_source")
        self.assertTrue(check["next_check_at"].startswith("2026-11-29"))
        c.close()

    def test_official_semantic_page_may_supply_description_and_time(self):
        html = BeautifulSoup(
            '<h1>La noche de las artes</h1>'
            '<time datetime="2026-12-05T20:00:00+00:00">5 diciembre</time>'
            '<meta name="description" content="' + DESCRIPTION + '">',
            "html.parser",
        )
        changes = mod.verified_page_evidence(BASE, html)
        self.assertEqual(changes.get("start"), "2026-12-05T20:00:00")
        self.assertEqual(changes.get("details"), DESCRIPTION)
        unrelated = BeautifulSoup(
            '<h1>Agenda cultural</h1>'
            '<time datetime="2026-12-05T20:00:00+00:00"></time>'
            '<meta name="description" content="' + DESCRIPTION + '">',
            "html.parser",
        )
        self.assertEqual(mod.verified_page_evidence(BASE, unrelated), {})
        wrong_date = BeautifulSoup(
            '<h1>La noche de las artes</h1>'
            '<time datetime="2026-12-06T20:00:00+00:00"></time>'
            '<meta name="description" content="' + DESCRIPTION + '">',
            "html.parser",
        )
        self.assertEqual(mod.verified_page_evidence(BASE, wrong_date), {})

    def test_semantic_fallback_cannot_override_conflicting_jsonld(self):
        page = BeautifulSoup(str(soup(name="Un evento distinto"))
            + '<h1>La noche de las artes</h1>'
              '<time datetime="2026-12-05"></time>'
              '<meta name="description" content="' + DESCRIPTION + '">',
            "html.parser")
        self.assertEqual(mod.verified_page_evidence(BASE, page), {})

    def test_official_utc_timestamps_use_canary_local_time(self):
        # Summer clock is UTC+1 in Canary Islands.
        result = mod.structured_evidence(
            {**BASE, "start": "2027-07-14"},
            soup(startDate="2027-07-14T19:00:00Z"),
        )
        self.assertEqual(result.get("start"), "2027-07-14T20:00:00")


if __name__ == "__main__":
    unittest.main()
