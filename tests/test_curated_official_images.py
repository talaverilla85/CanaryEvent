"""Keep D’Parranda event artwork tied to the correct official source."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import curated_official_images as media


class OfficialEventImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads((ROOT / "data/official_event_images.json").read_text(encoding="utf-8"))
        cls.events = json.loads((ROOT / "public/events.json").read_text(encoding="utf-8"))["events"]

    def test_each_audited_image_has_whitelisted_source_and_stable_identity(self):
        ids = set()
        for item in self.dataset["items"]:
            self.assertTrue(media.validated(item), item["image_url"])
            self.assertNotIn(item["id"], ids, "Duplicate curated event media")
            ids.add(item["id"])
            self.assertEqual(item["image_status"], "official_remote")

    def test_covers_are_exactly_attached_to_the_original_event(self):
        by_id = {event["id"]: event for event in self.events}
        for item in self.dataset["items"]:
            event = by_id.get(item["id"])
            # Expired events can disappear from the public export.
            if event is None:
                continue
            self.assertEqual(item["title"], event["title"])
            self.assertEqual(item["source_url"], event["source_url"])
            self.assertEqual(item["image_url"], event["image_url"])

    def test_wont_override_a_different_source_or_official_image(self):
        original = self.dataset["items"][0]
        mock = dict(id=original["id"],title="An unrelated event",source_url=original["source_url"],image_url="")
        self.assertEqual(media.apply([mock]),0)
        self.assertEqual(mock["image_url"],"")
        mock2 = dict(id=original["id"],title=original["title"],source_url=original["source_url"],image_url="https://example.org/verified.jpg")
        self.assertEqual(media.apply([mock2]),0)
        self.assertEqual(mock2["image_url"],"https://example.org/verified.jpg")
        mock3 = dict(id=original["id"],title=original["title"],source_url=original["source_url"],image_url="")
        self.assertEqual(media.apply([mock3]),1)
        self.assertEqual(mock3["image_url"],original["image_url"])

    def test_no_generic_site_social_image_appears_as_cover(self):
        for item in self.dataset["items"]:
            self.assertNotIn("/og-image.jpg",item["image_url"])
            self.assertNotIn("favicon",item["image_url"].lower())


if __name__ == "__main__":
    unittest.main()
