"""Official 2026 Mogán Mall raster-PDF transcription and source safeguards."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mogan_mall_official as source


class MoganMallProgrammeTests(unittest.TestCase):
    def test_official_pdf_has_fixed_season_and_image_attributed_to_organizer(self):
        rows = source.verified_entries(dt.date(2026, 11, 24))
        self.assertGreater(len(rows), 35)
        self.assertEqual(source.OFFICIAL_PDF_FILE_ID,
                         "1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v")
        for row in rows:
            self.assertEqual(row["source_name"], source.NAME)
            self.assertEqual(row["venue"], "Centro Comercial Mogán Mall")
            self.assertEqual(row["municipality"], "Mogán")
            self.assertEqual(row["source_url"], source.OFFICIAL_PDF)
            self.assertEqual(row["organizer_url"], "https://moganmall.com/navidad/")
            self.assertEqual(row["image_origin"], source.OFFICIAL_PDF)
            self.assertEqual(row["image_status"], "official_remote")
            self.assertEqual(row["image_url"], source.OFFICIAL_IMAGE)
            self.assertIsNone(row["free"])  # free entry is NOT asserted by PDF
            self.assertEqual(row["price"], "")
            self.assertIn("Tomás Roca Bosch", row["details"])
            self.assertIn("Consulta el programa", row["details"])

    def test_real_future_sessions_and_individual_times_are_precise(self):
        rows = source.verified_entries(dt.date(2026, 11, 24))
        self.assertTrue(any("Don Sonrisas" in e["title"] and
                            e["start"] == "2026-11-27T16:30:00" and
                            e["end"] == "2026-11-27T19:30:00" for e in rows))
        self.assertTrue(any("Jurassic Garden" in e["title"] and
                            e["start"] == "2026-11-28T18:00:00" for e in rows))
        self.assertTrue(any("Jurassic Garden" in e["title"] and
                            e["start"] == "2026-11-29T12:00:00" for e in rows))
        self.assertTrue(any("Miriam Santana" in e["title"] and
                            e["start"] == "2026-12-05T19:00:00" for e in rows))
        self.assertTrue(any("Canterbury" in e["title"] and
                            e["start"] == "2026-12-18T18:00:00" for e in rows))
        self.assertTrue(any("Papá Noel" in e["title"] and
                            e["start"] == "2026-12-23T17:30:00" for e in rows))
        self.assertTrue(any("Reyes Magos" in e["title"] and
                            e["start"] == "2027-01-04T17:30:00" for e in rows))
        self.assertFalse(any("Black Friday" in e["title"] or
                             "Magic Ticket" in e["title"] for e in rows))
        self.assertFalse(any(e["start"] < "2026-11-24" for e in rows))
        self.assertEqual(len({(e["title"], e["start"]) for e in rows}),
                         len(rows))

    def test_fountain_is_one_event_per_verified_friday_and_saturday(self):
        rows = source.verified_entries(dt.date(2026, 11, 24))
        fountain = [e for e in rows if "fuente especial" in e["title"]]
        self.assertEqual(
            [e["start"] for e in fountain],
            [f"{day}T20:00:00" for day in (
                "2026-12-04", "2026-12-05", "2026-12-11",
                "2026-12-12", "2026-12-18", "2026-12-19",
                "2026-12-25", "2026-12-26", "2027-01-01",
                "2027-01-02",
            )]
        )

    def test_rink_one_period_not_spurious_daily_events(self):
        rows = source.verified_entries(dt.date(2026, 12, 28))
        rink = [e for e in rows if "Pista de hielo" in e["title"]]
        self.assertEqual(len(rink), 1)
        self.assertEqual(rink[0]["start"], "2026-12-22T12:00:00")
        self.assertEqual(rink[0]["end"], "2027-01-06T20:00:00")
        self.assertIn("Abierta de 12:00 a 20:00 h", rink[0]["details"])

    def test_past_programmes_and_other_years_never_recycled(self):
        self.assertEqual(source.verified_entries(dt.date(2026, 11, 1)), [])
        self.assertEqual(source.verified_entries(dt.date(2027, 1, 7)), [])
        self.assertEqual(source.verified_entries(dt.date(2027, 11, 24)), [])

    def test_publishing_idempotence_and_independent_source_logging(self):
        conn=sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE source_log(
            source TEXT PRIMARY KEY, checked_at TEXT, found INTEGER,
            added INTEGER, changed INTEGER, error TEXT)""")
        records = {}
        def upsert(_conn, row):
            key=(row["title"],row["start"])
            if key in records:
                return "unchanged"
            records[key]=row
            return "added"
        first=source.synchronize(conn,"2026-11-24T08:00:00",
                                  dt.date(2026,11,24),upsert)
        self.assertEqual(first["error"],"")
        self.assertEqual(first["added"], first["found"])
        self.assertEqual(first["found"],len(records))
        self.assertGreater(first["found"],35)
        later=source.synchronize(conn,"2026-11-24T09:00:00",
                                  dt.date(2026,11,24),upsert)
        self.assertEqual(later["added"],0)
        self.assertEqual(later["found"],first["found"])
        count=conn.execute("SELECT COUNT(*) FROM source_log").fetchone()[0]
        self.assertEqual(count,1)
        self.assertEqual(
            conn.execute("SELECT source FROM source_log").fetchone()[0],
            source.NAME)
        conn.close()


if __name__ == "__main__":
    unittest.main()
