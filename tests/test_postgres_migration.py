"""Offline checks of the safe PostgreSQL migration path."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "dp_postgres_migration", ROOT / "scripts" / "postgres_migration.py"
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class PostgresMigrationTests(unittest.TestCase):
    def test_sqlite_catalog_is_valid_and_not_empty(self):
        rows, logs, catalog, cards, campaigns = migration.read_snapshot()
        self.assertGreater(len(rows), 0)
        self.assertGreater(len(cards), 0)
        self.assertEqual(len({x["id"] for x in rows}), len(rows))
        self.assertEqual(len({x["id"] for x in cards}), len(cards))
        self.assertTrue(all("id" in ad for ad in campaigns))
        self.assertIn("generated_at", catalog)

    def test_schema_prepares_manual_overrides_and_advertising(self):
        sql = migration.SCHEMA.read_text(encoding="utf-8")
        for table in ("events", "source_log", "published_events",
                      "event_overrides", "ad_campaigns", "ad_daily_stats"):
            self.assertIn("CREATE TABLE IF NOT EXISTS " + table, sql)
        self.assertIn("canonical_event_id BIGINT", sql)
        self.assertIn("review_status TEXT", sql)

    def test_reimports_preserve_editor_changes(self):
        source = (ROOT / "scripts" / "postgres_migration.py").read_text(encoding="utf8")
        self.assertIn("ON CONFLICT(id) DO NOTHING", source)
        self.assertNotIn("DROP TABLE", source)
        self.assertNotIn("TRUNCATE", source)
        self.assertIn("present != len(rows) or active != len(cards)", source)


if __name__ == "__main__":
    unittest.main()
