import re
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

HTML=(Path(__file__).resolve().parents[1]/"public"/"index.html").read_text(encoding="utf-8")

class MapContractTests(unittest.TestCase):
    def test_leaflet_stylesheet_integrity(self):
        # Map assets are downloaded only when opened; integrity protection
        # must still be present on the dynamically created stylesheet.
        soup=BeautifulSoup(HTML,"html.parser")
        self.assertIsNone(soup.find("link",href=re.compile("leaflet.css")))
        self.assertIn("async function openMap()",HTML)
        self.assertIn("try{await loadLeaflet()}",HTML)
        self.assertIn("css.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'",HTML)
        self.assertIn("css.integrity='sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY='",HTML)
        self.assertIn("script.integrity='sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo='",HTML)

    def test_map_controls_and_drilldown(self):
        soup=BeautifulSoup(HTML,"html.parser")
        for id in ("mapPanel","mapCanvas","mapList","mapSummary","mapMore","mapReset","closeMap"):
            self.assertIsNotNone(soup.find(id=id))
        self.assertIn("marker.on('click'",HTML)
        self.assertIn("state.mapSelected=key",HTML)
        self.assertIn("state.mapLimit+=16",HTML)
        self.assertIn("state.mapMunicipalities",HTML)
        self.assertIn("state.mapClusterKeys",HTML)
        self.assertIn("pixels[i].distanceTo(pixels[j])<55",HTML)
        self.assertIn("state.map.on('zoomend'",HTML)
        self.assertNotIn("ev.slice(0,20).map",HTML)

    def test_map_accuracy_explicit(self):
        self.assertIn("centro del municipio",HTML)
        self.assertIn("La posición es aproximada",HTML)

if __name__=="__main__":
    unittest.main()
