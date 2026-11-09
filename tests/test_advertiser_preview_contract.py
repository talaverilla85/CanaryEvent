"""Contracts for the two advertiser paths and full-page preview simulator."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdvertiserSimulatorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"public/anunciate/index.html").read_text(encoding="utf-8")
        cls.builder=(ROOT/"public/anunciate/landing.js").read_text(encoding="utf-8")
        cls.sim_html=(ROOT/"public/anunciate/simulador/index.html").read_text(encoding="utf-8")
        cls.sim_js=(ROOT/"public/anunciate/simulador/simulator.js").read_text(encoding="utf-8")
        cls.api=(ROOT/"api/advertise.js").read_text(encoding="utf-8")

    def test_two_public_advertiser_paths(self):
        self.assertIn('id="chooseInfo"',self.html)
        self.assertIn('id="chooseCreate"',self.html)
        self.assertIn('id="infoPanel"',self.html)
        self.assertIn('id="createPanel"',self.html)
        self.assertIn('id="showPreview"',self.html)
        self.assertIn('Ver en DParranda',self.html)

    def test_prices_and_sponsor_type_selector(self):
        self.assertIn('data-plan="local"',self.html)
        self.assertIn('data-plan="zona"',self.html)
        self.assertIn('data-plan="insular"',self.html)
        for price in ('19 €','49 €','99 €'):
            self.assertIn(price,self.html)
        self.assertIn('data-days="30"',self.html)
        self.assertIn('data-days="60"',self.html)
        self.assertNotIn('data-days="90"',self.html)
        self.assertIn("const PRICES={local:19,zona:49,insular:99}",self.builder)
        self.assertIn("days<1||days>60",self.api)
        self.assertIn('value="banner"',self.html)
        self.assertIn('value="evento"',self.html)

    def test_preview_is_new_page_with_real_events(self):
        self.assertIn("window.location.assign('/anunciate/simulador/')",self.builder)
        self.assertIn("sessionStorage.setItem('dp_ad_simulator_v1'",self.builder)
        self.assertIn('id="simFeed"',self.sim_html)
        self.assertIn('id="simSummary"',self.sim_html)
        self.assertIn("'/api/catalog'"," ".join(self.sim_js.split()))
        self.assertIn("'/events.json'",self.sim_js)
        self.assertIn("Patrocinado",self.sim_js)
        self.assertIn("i===4",self.sim_js)
        self.assertIn("GRID.append(eventCard({",self.sim_js)
        self.assertIn("GRID.append(sponsorBanner(draft))",self.sim_js)
        self.assertIn('href="/anunciate/#crear"',self.sim_html)
        self.assertIn('function restoreDraft()',self.builder)
        self.assertIn("storedArtwork=d.image",self.builder)

    def test_preview_is_private_no_payment_or_publication(self):
        self.assertNotIn("fetch(",self.builder)
        self.assertIn("method:'POST'",self.sim_js)
        self.assertIn("'/api/advertise-interest'",self.sim_js)
        self.assertIn('id="interestForm"',self.sim_html)
        self.assertIn('id="interestPrivacy"',self.sim_html)
        self.assertIn("campaign:{",self.sim_js)
        self.assertNotIn("image:draft.image",self.sim_js)
        self.assertNotIn("tax_id",self.sim_html)
        self.assertIn("cache:'no-store'",self.sim_js)
        self.assertIn("VISTA PREVIA · NO PUBLICADO",self.sim_html)
        self.assertNotIn("name=\"tax_id\"",self.html)
        self.assertNotIn("AriMar",self.html)
        self.assertIn("Librería La Esquina",self.html)
        self.assertIn("if(!enabled())return json(res,503",self.api)

if __name__=="__main__":
    unittest.main()
