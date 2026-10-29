"""Catch JavaScript startup regressions in Ochea's static homepage.

In particular, event loading must not be blocked by a handler attached to an
element removed during the homepage's responsive redesign.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


class OcheaHomepageContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (PUBLIC / "index.html").read_text(encoding="utf-8-sig")

    def test_every_document_id_accessor_exists(self):
        ids = set(re.findall(r'id="([^"]+)"', self.html))
        refs = set(re.findall(r"\$\('([^']+)'\)", self.html))
        self.assertFalse(refs - ids, "Missing elements block init(): " + ", ".join(sorted(refs - ids)))

    def test_catalog_loading_still_starts(self):
        self.assertIn("loadEvents();", self.html)
        self.assertIn("'/api/events'", self.html)
        self.assertIn('id="eventsGrid"', self.html)

    def test_brand_and_filter_modal(self):
        for anchor in ('src="/ochea-logo.svg?v=4"', 'id="openFiltersBtn"',
                       'id="filtersPanel"', 'id="locationButton"',
                       'id="islandOptions"', 'id="applyFiltersBtn"'):
            self.assertIn(anchor, self.html)
        for name in ("Gran Canaria", "Tenerife", "Lanzarote", "Fuerteventura",
                     "La Palma", "La Gomera", "El Hierro", "La Graciosa"):
            self.assertIn("'" + name + "'", self.html)

    def test_manifest_icons_exist_and_are_versioned(self):
        manifest = json.loads((PUBLIC / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["short_name"], "Ochea")
        for icon in manifest["icons"]:
            self.assertIn("?v=4", icon["src"])
            self.assertTrue((PUBLIC / icon["src"].split("?", 1)[0].lstrip("/")).is_file())
        self.assertTrue((PUBLIC / "apple-touch-icon.png").is_file())


if __name__ == "__main__":
    unittest.main()
