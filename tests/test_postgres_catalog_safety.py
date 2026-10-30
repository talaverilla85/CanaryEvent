"""Safety checks for DParranda PostgreSQL migration."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PostgresCatalogSafetyTests(unittest.TestCase):
    def test_postgres_catalog_schema(self):
        schema = (ROOT / "sql/postgres_schema.sql").read_text(encoding="utf-8")
        for table in ("events", "published_events", "source_log", "event_overrides", "ad_campaigns"):
            self.assertIn("CREATE TABLE IF NOT EXISTS " + table, schema)
        self.assertNotIn("DROP TABLE", schema)
        self.assertNotIn("TRUNCATE", schema)

    def test_catalog_ids_are_unique(self):
        data = json.loads((ROOT / "public/events.json").read_text(encoding="utf-8"))
        cards = data.get("events", [])
        self.assertGreater(len(cards), 0)
        self.assertEqual(len(cards), len({card["id"] for card in cards}))

if __name__ == "__main__":
    unittest.main()
