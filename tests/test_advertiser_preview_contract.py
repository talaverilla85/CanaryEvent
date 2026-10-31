"""Advertising enquiry demo should work before personal-data intake is enabled."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdvertiserPreviewContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"public/anunciate/index.html").read_text(encoding="utf-8")
        cls.js=(ROOT/"public/anunciate/form.js").read_text(encoding="utf-8")
        cls.api=(ROOT/"api/advertise.js").read_text(encoding="utf-8")

    def test_preview_available_without_submission(self):
        self.assertIn('id="submit" class="btn" type="button"',self.html)
        self.assertIn('id="advertiserDemo"',self.html)
        self.assertIn('function previewAdvertiser()',self.js)
        preview=self.js.split("function previewAdvertiser()",1)[1].split("previewButton.addEventListener",1)[0]
        self.assertNotIn("fetch(",preview)
        self.assertNotIn("billing_",preview)
        self.assertNotIn("tax_id",preview)
        self.assertIn("demo.hidden=false",preview)

    def test_real_submission_stays_separate_and_privacy_gated(self):
        self.assertIn('id="sendProposal" class="btn light" type="submit" hidden',self.html)
        self.assertIn("sendButton.hidden=!enabled",self.js)
        self.assertIn("enabled=response.ok&&data.enabled===true&&!!data.privacy_url",self.js)
        self.assertIn("if(!enabled())return json(res,503",self.api)

    def test_public_campaign_maximum_is_60_days(self):
        self.assertNotIn('<option value="90">',self.html)
        self.assertNotIn("days>90",self.api)
        self.assertIn("days>60",self.api)
        self.assertIn('<option value="60">60 días</option>',self.html)

if __name__=="__main__":
    unittest.main()
