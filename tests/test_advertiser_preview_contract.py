"""Contracts for DParranda's simple, no-login advertiser paths."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class AdvertiserPreviewContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "public/anunciate/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "public/anunciate/landing.js").read_text(encoding="utf-8")
        cls.api = (ROOT / "api/advertise.js").read_text(encoding="utf-8")

    def test_two_clear_starting_routes(self):
        self.assertIn('id="chooseInfo"', self.html)
        self.assertIn('id="chooseCreate"', self.html)
        self.assertIn('id="infoPanel"', self.html)
        self.assertIn('id="createPanel"', self.html)
        self.assertIn('id="infoToCreate"', self.html)
        self.assertIn('id="showPreview"', self.html)
        self.assertIn('/anunciate/landing.js?v=2', self.html)

    def test_prices_and_limit(self):
        for price in ('19 €','49 €','99 €'):
            self.assertIn(price, self.html)
        self.assertIn('data-days="30"', self.html)
        self.assertIn('data-days="60"', self.html)
        self.assertNotIn('data-days="90"', self.html)
        self.assertIn("const PRICES={local:19,zona:49,insular:99}", self.js)
        self.assertIn("days<1||days>60", self.api)
        self.assertNotIn("days>90", self.api)
        self.assertIn("chosen.length<(plan==='local'?1:4)", self.js)

    def test_ad_preview_does_not_submit_or_charge(self):
        self.assertIn("function showPanel(which)", self.js)
        self.assertIn("id=\"checkoutInfo\"", self.html)
        self.assertIn("id=\"previewSection\"", self.html)
        self.assertIn("id=\"eventDetails\"", self.html)
        self.assertIn("id=\"eventDate\"", self.html)
        self.assertIn("id=\"eventVenue\"", self.html)
        self.assertIn("id=\"reviewEvent\"", self.html)
        self.assertIn("resetPreview()", self.js)
        self.assertIn("No se ha creado ni cobrado ninguna campaña.", self.js)
        self.assertNotIn("fetch(", self.js)
        self.assertNotIn("XMLHttpRequest", self.js)

    def test_customer_data_still_gated_by_privacy(self):
        self.assertIn("if(!enabled())return json(res,503", self.api)
        self.assertNotIn('name="tax_id"', self.html)
        self.assertNotIn('name="billing_address"', self.html)
        self.assertIn("Los pagos online todavía no están habilitados.", self.html)

if __name__ == "__main__":
    unittest.main()
