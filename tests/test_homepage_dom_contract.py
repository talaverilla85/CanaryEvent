"""Catch JavaScript startup regressions in D’Parranda's static homepage.

In particular, event loading must not be blocked by a handler attached to an
element removed during the homepage's responsive redesign.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


class DParrandaHomepageContract(unittest.TestCase):
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
        self.assertIn('<script src="/temporal.js?v=1"></script>', self.html)
        self.assertTrue((PUBLIC / "temporal.js").is_file())
        self.assertIn("DParrandaTime.hasFinished(e,localTimeKey())", self.html)
        self.assertIn("setInterval(refreshEventTime,30000)", self.html)

    def test_brand_and_filter_modal(self):
        for anchor in ('src="/brand/dparranda-logo.svg?v=6"', 'id="openFiltersBtn"',
                       'id="filtersPanel"', 'id="locationButton"',
                       'id="islandOptions"', 'id="applyFiltersBtn"'):
            self.assertIn(anchor, self.html)
        for name in ("Gran Canaria", "Tenerife", "Lanzarote", "Fuerteventura",
                     "La Palma", "La Gomera", "El Hierro", "La Graciosa"):
            self.assertIn("'" + name + "'", self.html)

    def test_mobile_install_entry_and_sponsor_branding(self):
        anchors = (
            'id="dpInstallDock"', 'id="dpInstallAction"', 'id="dpInstallDismiss"',
            'id="dpInstallGuideOverlay"', 'id="dpInstallGuideClose"',
            'id="dpInstallGuideDone"', 'id="dpInstallGuideSteps"',
            '<script src="/install_prompt.js?v=1"></script>',
            'class="sponsor-slot"', 'ESPACIO PATROCINADO',
        )
        for anchor in anchors:
            self.assertIn(anchor, self.html)
        self.assertTrue((PUBLIC / "install_prompt.js").is_file())
        css = (PUBLIC / "brand/dparranda-theme.css").read_text(encoding="utf-8")
        self.assertIn(".dp-install-dock{", css)
        self.assertIn("position:fixed;", css)
        self.assertIn("bottom:calc(82px + env(safe-area-inset-bottom,0px))", css)
        self.assertIn("#D2ECF0", css)
        sw = (PUBLIC / "sw.js").read_text(encoding="utf-8")
        self.assertIn("'/install_prompt.js'", sw)

    def test_quick_discovery_and_event_sharing(self):
        """Quick filters and share buttons must remain wired into catalog state."""
        for fragment in (
            'data-quick-when="today"',
            'data-quick-when="weekend"',
            'data-quick-free',
            'state.freeOnly=false;',
            "(!state.freeOnly||e.free===1)",
            'data-share="${e.id}"',
            "function shareEvent(id)",
            "function eventShareUrl(id)",
            "function clearEventUrl()",
            "document.querySelector('[data-quick-free]').onclick",
        ):
            self.assertIn(fragment, self.html)
        css = (PUBLIC / "brand/dparranda-theme.css").read_text(encoding="utf-8")
        self.assertIn(".dp-shortcut.active", css)
        self.assertIn(".event-card .card-share-btn", css)

    def test_manifest_icons_exist_and_are_versioned(self):
        manifest = json.loads((PUBLIC / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["short_name"], "D’Parranda")
        for icon in manifest["icons"]:
            self.assertRegex(icon["src"], r"\?v=\d+$")
            self.assertTrue((PUBLIC / icon["src"].split("?", 1)[0].lstrip("/")).is_file())
        self.assertTrue((PUBLIC / "apple-touch-icon.png").is_file())
        self.assertTrue((PUBLIC / "brand/dparranda-theme.css").is_file())
        for filename in ("dparranda-logo.svg", "dparranda-compact.svg",
                         "dparranda-monochrome.svg", "dparranda-negative.svg",
                         "dparranda-icon.svg", "dparranda-favicon.svg"):
            self.assertTrue((PUBLIC / "brand" / filename).is_file())
        self.assertIn("Disfruta de tus islas.", self.html)
        self.assertNotIn("Ochea", self.html)
        self.assertIn('id="loadingGrid"', self.html)


if __name__ == "__main__":
    unittest.main()
