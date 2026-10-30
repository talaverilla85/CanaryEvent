import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
class SponsorTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/"public"/"ads.json").read_text(encoding="utf8"))
        cls.index=(ROOT/"public"/"index.html").read_text(encoding="utf8")

    def test_founder_ad_only_one_with_direct_order_url(self):
        self.assertEqual(len(self.config["ads"]),1)
        a=self.config["ads"][0]
        self.assertEqual(a["id"],"arimar-fundador")
        self.assertTrue(a["enabled"] and a["permanent"])
        self.assertEqual(a["kind"],"house")
        self.assertEqual(a["button_url"],"https://arimarfoodlab.es/pedir")
        self.assertEqual(a["button_text"],"Pedir online")
        self.assertEqual(a["disclosure"],"Publicidad")
        self.assertIsNone(a["ends_at"])

    def test_photo_stored_locally(self):
        a=self.config["ads"][0]
        self.assertTrue(a["image"].startswith("/sponsors/"))
        self.assertGreater((ROOT/"public"/a["image"].lstrip("/")).stat().st_size,10000)

    def test_separate_full_width_ad_not_event(self):
        self.assertIn("grid-column:1/-1",self.index)
        self.assertIn('class="sponsor-slot"',self.index)
        self.assertIn("ESPACIO PATROCINADO",self.index)
        self.assertIn("PUBLICIDAD",self.index)
        self.assertIn("shown.map((e,i)",self.index)
        self.assertIn("state.tab==='explore'",self.index)
        self.assertIn("rel=\"sponsored noopener noreferrer\"",self.index)
        theme=(ROOT/"public"/"brand/dparranda-theme.css").read_text(encoding="utf8")
        self.assertIn(".events-grid > .sponsor-slot{",theme)
        self.assertIn("background:linear-gradient(124deg,#D2ECF0",theme)
        self.assertIn("border:2px solid #78BFC7",theme)

if __name__=="__main__":unittest.main()
