"""Regression for targeted, fair automatic SEO enrichment."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import event_enrichment as mod
from test_event_enrichment_queue import BASE, DESCRIPTION, db, put, soup


def candidate(group, idx):
    base = {
        **BASE,
        "id": idx,
        "title": "La noche de las artes",
        "start": "2026-12-05T20:00:00",
        "end": None,
        "venue": "Teatro de la Villa",
        "accuracy": "venue",
        "details": DESCRIPTION,
        "source_url": f"https://ingenio.es/events/priority-{idx}/",
    }
    if group == "one":
        base["details"] = "Programación oficial del recinto."
    if group == "two":
        base["details"] = "Programación oficial del recinto."
        base["accuracy"] = "municipality"
    if group == "deep":
        base["start"] = "2026-12-05"
        base["details"] = ""
        base["accuracy"] = "municipality"
        base["venue"] = "Lugar por confirmar"
    return base


class PriorityTests(unittest.TestCase):
    def test_mandatory_venue_and_accuracy_are_separate_blockers(self):
        e = candidate("deep", 101)
        missing = mod.gaps(e)
        self.assertIn("recinto", missing)
        self.assertIn("ubicacion", missing)
        self.assertEqual(mod.priority_bucket(e, missing), "deep")
        named = candidate("one", 102)
        self.assertEqual(mod.seo_blockers(named), ("descripcion",))
        self.assertEqual(mod.priority_bucket(named), "one")
        complete = candidate("polish", 103)
        self.assertTrue(mod.seo_ready(complete))
        self.assertEqual(mod.priority_bucket(complete), "polish")
        self.assertIn("cartel", mod.gaps(complete))
        self.assertIn("precio", mod.gaps(complete))

    def test_eight_slot_priority_reserves_deep_and_polish_capacity(self):
        conn = db()
        for group, start, count in [
            ("one", 100, 12),
            ("two", 200, 8),
            ("deep", 300, 5),
            ("polish", 400, 4),
        ]:
            for i in range(start, start + count):
                put(conn, **candidate(group, i))
        urls = []
        def fetch(url):
            urls.append(url)
            return soup(name="Un evento diferente")
        report = mod.enrich(
            conn, "2026-11-23T09:00:00", date(2026, 11, 23),
            fetch_html=fetch, max_requests=8, max_events=8
        )
        self.assertEqual(report["checked"], 8)
        self.assertEqual(report["requests"], 8)
        self.assertEqual(report["checked_by_priority"],
                         {"one": 4, "two": 2, "deep": 1, "polish": 1})
        self.assertEqual(report["one_seo_gap"], 12)
        self.assertEqual(report["two_seo_gaps"], 8)
        self.assertEqual(report["near_ready"], 20)
        self.assertEqual(len(urls), 8)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM event_enrichment_checks").fetchone()[0], 8)
        conn.close()

    def test_buckets_fill_open_slots_without_losing_request_capacity(self):
        conn = db()
        for i in range(101, 109):
            put(conn, **candidate("one", i))
        report = mod.enrich(
            conn, "2026-11-23T09:00:00", date(2026, 11, 23),
            fetch_html=lambda url: soup(name="Otro evento"),
            max_requests=8, max_events=8
        )
        self.assertEqual(report["checked_by_priority"]["one"], 8)
        self.assertEqual(report["requests"], 8)
        conn.close()

    def test_due_rechecks_cannot_starve_behind_continuous_new_arrivals(self):
        events = [candidate("one", idx) for idx in range(101, 115)]
        previous = {"checked_at": "2026-11-19T08:00:00", "attempts": 1}
        pending = [
            (event, mod.gaps(event), previous if i < 3 else None)
            for i, event in enumerate(events)
        ]
        ordered = mod.prioritize_pending(pending, "2026-11-23")
        self.assertEqual(len(ordered), len(pending))
        self.assertEqual(len({e["id"] for e, _, _ in ordered}), len(events))
        self.assertEqual(sum(bool(item[2]) for item in ordered[:8]), 2)

    def test_upcoming_sessions_take_precedence_over_old_long_running_items(self):
        old = candidate("one", 101)
        old["start"] = "2026-09-01T18:00:00"
        old["end"] = "2026-12-15"
        upcoming = candidate("one", 102)
        ordered = mod.prioritize_pending(
            [(old, mod.gaps(old), None), (upcoming, mod.gaps(upcoming), None)],
            "2026-11-23"
        )
        self.assertEqual(ordered[0][0]["id"], 102)

    def test_verified_evidence_still_required_to_make_event_seo_ready(self):
        conn = db()
        e = candidate("one", 101)
        put(conn, **e)
        report = mod.enrich(
            conn, "2026-11-23T08:00:00", date(2026, 11, 23),
            fetch_html=lambda url: soup()
        )
        self.assertEqual(report["newly_eligible"], 1)
        self.assertEqual(report["checked_by_priority"]["one"], 1)
        self.assertTrue(mod.seo_ready(dict(conn.execute("SELECT * FROM events").fetchone())))
        self.assertTrue(conn.execute(
            "SELECT 1 FROM event_enrichment_proofs WHERE field_name='details'"
        ).fetchone())
        conn.close()

    def test_unverified_sources_do_not_get_to_index_via_priority(self):
        conn = db()
        put(conn, **candidate("one", 101))
        report = mod.enrich(
            conn, "2026-11-23T08:00:00", date(2026, 11, 23),
            fetch_html=lambda url: BeautifulSoup(
                '<h1>Una actividad diferente</h1>'
                '<time datetime="2026-12-05T20:00:00"></time>'
                '<meta name="description" content="' + DESCRIPTION + '">',
                "html.parser",
            )
        )
        self.assertEqual(report["newly_eligible"], 0)
        self.assertEqual(report["verified"], 0)
        self.assertFalse(mod.seo_ready(dict(conn.execute("SELECT * FROM events").fetchone())))
        conn.close()


if __name__ == "__main__":
    unittest.main()
