"""Only real public-catalog changes may be reported as new events."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from catalog_changes import compare_public_catalogs,read_published


class PublicCatalogDeltaTests(unittest.TestCase):
    def test_real_addition_modification_and_expiration(self):
        prior=[{"id":1,"title":"Taller","venue":"Centro cultural"},
               {"id":2,"title":"Concierto","venue":"Teatro"}]
        current=[{"id":1,"title":"Taller","venue":"Auditorio"},
                 {"id":3,"title":"Feria","venue":"Plaza"}]
        self.assertEqual(compare_public_catalogs(prior,current),
                         {"available":True,"new":1,"updated":1,"removed":1})

    def test_source_discovery_does_not_count_unpublished_candidate(self):
        prior=[{"id":5,"title":"Publicado","start":"2026-11-10"}]
        current=[{"id":5,"title":"Publicado","start":"2026-11-10"}]
        self.assertEqual(compare_public_catalogs(prior,current)["new"],0)

    def test_export_metadata_does_not_create_fake_update(self):
        prior=[{"id":5,"title":"Música","updated_at":"2026-11-04","last_seen":"2026-11-04"}]
        current=[{"id":5,"title":"Música","updated_at":"2026-11-05","last_seen":"2026-11-05"}]
        self.assertEqual(compare_public_catalogs(prior,current)["updated"],0)

    def test_bad_baseline_does_not_report_all_events_as_new(self):
        self.assertEqual(compare_public_catalogs(None,[{"id":1,"title":"A"}]),
                         {"available":False,"new":0,"updated":0,"removed":0})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"events.json"
            self.assertIsNone(read_published(p))
            p.write_text("{invalid",encoding="utf8")
            self.assertIsNone(read_published(p))
            p.write_text(json.dumps({"events":[{"id":1,"title":"OK"}]}),encoding="utf8")
            self.assertEqual(read_published(p)[0]["title"],"OK")


if __name__=="__main__":
    unittest.main()
