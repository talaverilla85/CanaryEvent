"""Regression checks for individually verified source URLs in D'Parranda."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import curated_official_links
import curated_official_images

class VerifiedSourceLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events={e["id"]:e for e in json.loads((ROOT/"public/events.json").read_text(encoding="utf8"))["events"]}
        cls.links=json.loads((ROOT/"data/official_event_links.json").read_text(encoding="utf8"))["items"]
        cls.images=json.loads((ROOT/"data/official_event_images.json").read_text(encoding="utf8"))["items"]

    def test_links_are_event_specific_and_live_in_published_catalog(self):
        self.assertEqual(len(self.links),5)
        for item in self.links:
            self.assertTrue(curated_official_links.validated(item),item)
            event=self.events.get(item["id"])
            if event is None:continue  # Future sync may drop an expired entry.
            self.assertEqual(event["title"],item["title"])
            self.assertEqual(event["source_url"],item["verified_url"])
            self.assertTrue(item["verified_url"].startswith("https://"))

    def test_override_is_bound_to_verified_old_url_and_title(self):
        for item in self.links:
            e={"id":item["id"],"title":item["title"],"source_url":item["source_url"]}
            self.assertEqual(curated_official_links.apply([e]),1)
            self.assertEqual(e["source_url"],item["verified_url"])
            bad=dict(e,source_url="https://example.com/general")
            self.assertEqual(curated_official_links.apply([bad]),0)
            altered={"id":item["id"],"title":"Different activity","source_url":item["source_url"]}
            self.assertEqual(curated_official_links.apply([altered]),0)

    def test_verified_media_matches_source_and_images(self):
        additions={105,530,560,633,634,635}
        curated={e["id"]:e for e in self.images if e["id"] in additions}
        self.assertEqual(set(curated),additions)
        for id,media in curated.items():
            self.assertTrue(curated_official_images.validated(media),id)
            published=self.events.get(id)
            if published is None:continue
            self.assertEqual(published["source_url"],media["source_url"])
            self.assertEqual(published["image_url"],media["image_url"])
            self.assertEqual(published["image_status"],"official_remote")

    def test_no_website_social_logo_as_event_photo(self):
        for media in self.images:
            self.assertNotIn("/og-image.jpg",media["image_url"])
            self.assertNotIn("favicon",media["image_url"].lower())

if __name__=="__main__":
    unittest.main()
