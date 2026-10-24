import re
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

HTML=(Path(__file__).resolve().parents[1]/"public"/"index.html").read_text(encoding="utf-8")

class MapContractTests(unittest.TestCase):
    def test_leaflet_stylesheet_integrity(self):
        soup=BeautifulSoup(HTML,"html.parser")
        link=soup.find("link",href=re.compile("leaflet.css"))
        self.assertIsNotNone(link)
        self.assertEqual(link.get("integrity"),
            "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=")

    def test_map_controls_and_drilldown(self):
        soup=BeautifulSoup(HTML,"html.parser")
        for id in ("mapPanel","mapCanvas","mapList","mapSummary","mapMore","mapReset","closeMap"):
            self.assertIsNotNone(soup.find(id=id))
        self.assertIn("marker.on('click'",HTML)
        self.assertIn("state.mapSelected=key",HTML)
        self.assertIn("state.mapLimit+=16",HTML)
        self.assertIn("state.mapEntries.length",HTML)
        self.assertNotIn("ev.slice(0,20).map",HTML)

    def test_map_accuracy_explicit(self):
        self.assertIn("centro del municipio",HTML)
        self.assertIn("La posición es aproximada",HTML)

if __name__=="__main__":
    unittest.main()
