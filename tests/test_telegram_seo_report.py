"""Bot SEO: truthful metrics, one weekly digest, persistent critical alerts."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import telegram_seo_report as seo

NOW = dt.datetime(2026, 11, 22, 20, 0, tzinfo=dt.timezone.utc)
URLS = "https://dparranda.es/evento/"
XML = ('<?xml version="1.0" encoding="UTF-8"?>'
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
       '<url><loc>' + URLS + '654</loc></url>'
       '<url><loc>' + URLS + '655</loc></url></urlset>')


class Response:
    def __init__(self, *, content=b"", json_value=None, status=200, type_="application/xml"):
        self.content = content
        self.status_code = status
        self.headers = {"content-type": type_}
        self.json_value = json_value

    def json(self):
        return self.json_value


class Session:
    def __init__(self, *, xml=XML, catalog=None, sitemap_status=200):
        self.xml = xml
        self.catalog = catalog if catalog is not None else {
            "events": [{"id": 654}, {"id": 655}, {"id": 656},
                       {"id": -28220261122},
                       {"id": 999, "paid_promotion": True}]}
        self.sitemap_status = sitemap_status

    def get(self, url, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] > 0
        if url == seo.SITEMAP_URL:
            return Response(content=self.xml.encode(), status=self.sitemap_status)
        if url == seo.CATALOG_URL:
            return Response(json_value=self.catalog, type_="application/json")
        raise AssertionError("Unexpected network URL")


class WeeklyTests(unittest.TestCase):
    def test_live_sitemap_and_catalog_are_independent_of_google_indexing(self):
        session = Session()
        self.assertEqual(seo.get_sitemap(session=session), {654, 655})
        self.assertEqual(seo.get_catalog(session=session), {654, 655, 656})
        snap = seo.weekly_data(NOW, {654, 655}, {654, 655, 656}, {}, 4)
        self.assertEqual(snap["pending_candidates"], 1)
        self.assertEqual(snap["verified_events_last_7d"], 4)
        msg = seo.make_weekly_message(snap)
        self.assertIn("primera medición", msg)
        self.assertIn("Sin medición anterior", msg)
        self.assertIn("no equivalen a páginas ya indexadas", msg)
        self.assertNotIn("30 nuevas", msg)

    def test_weekly_baseline_tracks_new_and_expired_ids(self):
        previous = {"week_ending": "2026-11-15", "eligible_ids": [653, 654]}
        snapshot = seo.weekly_data(NOW, {654, 655}, {654, 655, 656}, previous, 2)
        self.assertEqual(snapshot["previous_eligible_count"], 2)
        self.assertEqual(snapshot["newly_eligible"], 1)
        self.assertEqual(snapshot["no_longer_eligible"], 1)
        self.assertEqual(snapshot["pending_candidates"], 1)
        self.assertIn("Fichas que dejaron de ser aptas", seo.make_weekly_message(snapshot))

    def test_duplicate_and_unknown_sitemap_entries_are_rejected(self):
        for invalid in (
            XML.replace(URLS + "655", URLS + "654"),
            XML.replace(URLS + "655", "https://evil.example/evento/655"),
            "<html>hello</html>",
        ):
            with self.subTest(invalid=invalid[-70:]):
                with self.assertRaises(ValueError):
                    seo.get_sitemap(session=Session(xml=invalid))

    def test_weekly_sends_once_and_persists_only_after_telegram_confirmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "weekly.json"
            db = Path(tmp) / "events.sqlite"
            with sqlite3.connect(db) as sql:
                sql.execute("CREATE TABLE event_enrichment_proofs(event_id INTEGER, verified_at TEXT)")
                sql.executemany("INSERT INTO event_enrichment_proofs VALUES(?,?)", [
                    (654, "2026-11-22T10:00:00+00:00"),
                    (654, "2026-11-22T18:00:00+00:00"),
                    (655, "2026-11-13T18:00:00+00:00"),
                    (800, "2026-11-22T18:00:00+00:00"),
                ])
            sql.close()  # SQLite context manager does not close the file on Windows.
            with patch.object(seo, "send", return_value=False) as mock:
                result = seo.weekly(NOW, session=Session(), token="secret", chat="id",
                                    state_path=state, db_path=db)
                self.assertEqual(result, 1)
                self.assertFalse(state.exists())
                self.assertEqual(mock.call_count, 1)
            with patch.object(seo, "send", return_value=True) as mock:
                result = seo.weekly(NOW, session=Session(), token="secret", chat="id",
                                    state_path=state, db_path=db)
                self.assertEqual(result, 0)
                self.assertEqual(mock.call_count, 1)
                snap = seo.read_json(state)
                self.assertEqual(snap["eligible_ids"], [654, 655])
                self.assertEqual(snap["verified_events_last_7d"], 1)
                again = seo.weekly(NOW, session=Session(), token="secret", chat="id",
                                   state_path=state, db_path=db)
                self.assertEqual(again, 0)
                self.assertEqual(mock.call_count, 1)

    def test_invalid_public_sitemap_never_emits_misleading_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(seo, "send", return_value=True) as mock:
                status = seo.weekly(NOW, session=Session(sitemap_status=503),
                                    state_path=Path(tmp) / "weekly.json",
                                    db_path=Path(tmp) / "sqlite")
                self.assertEqual(status, 1)
                mock.assert_not_called()

    def test_no_dry_run_writes_or_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "weekly.json"
            with patch.object(seo, "send") as mock:
                self.assertEqual(seo.weekly(NOW, session=Session(), dry_run=True,
                                            state_path=dest,
                                            db_path=Path(tmp) / "missing.sqlite"), 0)
                self.assertFalse(dest.exists())
                mock.assert_not_called()

    def test_monitor_avoids_one_off_noise_and_repeats(self):
        fresh = {"checked_at": NOW.isoformat()}
        state, message = seo.monitor_result(NOW, fresh, False, {})
        self.assertEqual(state["sitemap_failures"], 1)
        self.assertIsNone(message)
        state, message = seo.monitor_result(NOW + dt.timedelta(days=1),
                                            {"checked_at": (NOW + dt.timedelta(days=1)).isoformat()},
                                            False, state)
        self.assertIn("dos comprobaciones", message)
        self.assertTrue(state["sitemap_alerted"])
        again, message = seo.monitor_result(NOW + dt.timedelta(days=2),
                                            {"checked_at": (NOW + dt.timedelta(days=2)).isoformat()},
                                            False, state)
        self.assertIsNone(message)
        recovered, message = seo.monitor_result(NOW + dt.timedelta(days=3),
                                            {"checked_at": (NOW + dt.timedelta(days=3)).isoformat()},
                                            True, again)
        self.assertIn("recuperado", message)
        self.assertFalse(recovered["sitemap_alerted"])

    def test_enrichment_inactivity_warns_only_after_72h_and_recovers(self):
        recent = {"checked_at": "2026-11-20T20:01:00Z"}
        self.assertFalse(seo.enrichment_stale(NOW, recent))
        old = {"checked_at": "2026-11-18T18:00:00Z"}
        self.assertTrue(seo.enrichment_stale(NOW, old))
        state, message = seo.monitor_result(NOW, old, True, {})
        self.assertIn("72 horas", message)
        again, message = seo.monitor_result(NOW, old, True, state)
        self.assertIsNone(message)
        recovered, message = seo.monitor_result(NOW, recent, True, again)
        self.assertIn("SEO recuperado", message)
        self.assertFalse(recovered["enrichment_alerted"])

    def test_daily_monitor_persists_state_only_for_alerts_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = Path(tmp) / "monitor.json"
            report = Path(tmp) / "status.json"
            seo.save_json(report, {"checked_at": NOW.isoformat()})
            with patch.object(seo, "send", return_value=True) as mock:
                healthy = seo.health(NOW, session=Session(), token="secret",
                                     chat="id", state_path=monitor, report_path=report)
                self.assertEqual(healthy, 0)
                mock.assert_not_called()
                self.assertFalse(monitor.exists())
                first = seo.health(NOW, session=Session(sitemap_status=503),
                                   token="secret", chat="id",
                                   state_path=monitor, report_path=report)
                self.assertEqual(first, 0)
                self.assertEqual(seo.read_json(monitor)["sitemap_failures"], 1)
                self.assertEqual(mock.call_count, 0)
                second = seo.health(NOW + dt.timedelta(days=1),
                                    session=Session(sitemap_status=503),
                                    token="secret", chat="id",
                                    state_path=monitor, report_path=report)
                self.assertEqual(second, 0)
                self.assertEqual(mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
