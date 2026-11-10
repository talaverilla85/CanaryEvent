"""Regression tests: contract request belongs underneath the advertised preview."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InlineContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'public/anunciate/simulador/index.html').read_text('utf8')
        cls.script=(ROOT/'public/anunciate/simulador/simulator.js').read_text('utf8')
        cls.admin=(ROOT/'api/admin.js').read_text('utf8')
        cls.panel=(ROOT/'public/admin/admin.js').read_text('utf8')
        cls.admin_html=(ROOT/'public/admin/index.html').read_text('utf8')
    def test_call_to_action_directly_after_sponsored_preview(self):
        self.assertIn("function contractCallout(draft)",self.script)
        self.assertIn("GRID.append(sponsorBanner(draft));GRID.append(contractCallout(draft))",self.script)
        self.assertIn("GRID.append(contractCallout(draft));",self.script)
        self.assertIn("wrapper.append($('interestSection'))",self.script)
        self.assertIn("section.hidden=!section.hidden",self.script)
        self.assertIn("button.setAttribute('aria-expanded'",self.script)
        self.assertIn("section.hidden=true;",self.script)
        self.assertIn(".inline-contract{grid-column:1/-1",self.html)
        self.assertIn('Solicitar contratación',self.script)
    def test_no_payments_and_safe_admin_diagnosis(self):
        self.assertIn("advertising-intake-config",self.admin)
        self.assertIn("if(!authenticated(req))",self.admin)
        self.assertIn("receiving_proposals:leads&&privacy",self.admin)
        self.assertIn("DPARRANDA_PRIVACY_URL",self.admin)
        self.assertIn("DPARRANDA_LEADS_ENABLED",self.admin)
        self.assertIn("loadAdvertisingIntake()",self.panel)
        self.assertIn('id="adopsIntake"',self.admin_html)
        self.assertIn("DPARRANDA_LEADS_ENABLED = true",self.panel)
        self.assertIn("settings/environment-variables",self.panel)
        self.assertNotIn('Stripe Checkout',self.script)
if __name__=="__main__":unittest.main()
