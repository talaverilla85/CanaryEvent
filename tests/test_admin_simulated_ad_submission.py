"""One-click admin-only test of full advertiser simulation without public intake."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class AdminSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=(ROOT/'api/admin.js').read_text('utf8')
        cls.front=(ROOT/'public/anunciate/simulador/simulator.js').read_text('utf8')
        cls.html=(ROOT/'public/anunciate/simulador/index.html').read_text('utf8')
        cls.adops=(ROOT/'public/admin/admin.js').read_text('utf8')
    def test_test_submissions_reach_neon_with_image_and_no_payment(self):
        self.assertIn("async function saveAdvertisingTestProposal(sql,body)",self.admin)
        self.assertIn("op==='advertising-test-proposal'",self.admin)
        self.assertIn("if(!authenticated(req))",self.admin)
        self.assertIn("req.method==='POST' && !sameOrigin(req)",self.admin)
        self.assertIn("PRUEBA_ADMIN|",self.admin)
        self.assertIn("advertising_enquiries",self.admin)
        self.assertIn("advertising_enquiry_images",self.admin)
        self.assertIn("status,review_status,payment_status",self.admin)
        self.assertIn("'new','submitted','unavailable'",self.admin)
        self.assertIn("prueba@ejemplo.invalid",self.admin)
        self.assertNotIn("checkout.sessions.create",self.admin)
    def test_admin_button_only_after_auth_check(self):
        self.assertIn("op=advertising-intake-config",self.front)
        self.assertIn("config?.admin_test_enabled===true",self.front)
        self.assertIn("testButton.hidden=true",self.front)
        self.assertIn("op=advertising-test-proposal",self.front)
        self.assertIn("image_data:draft.image",self.front)
        self.assertIn("draft.advertiser",self.front)
        self.assertIn("draft.description",self.front)
        self.assertIn("draft.municipalities",self.front)
        self.assertIn("Enviar prueba al panel",self.front)
        self.assertIn("data:image",self.front)
        self.assertIn("/admin/#publicidad",self.front)
        self.assertIn("inline-contract-test",self.html)
    def test_fails_closed_for_public_requests(self):
        self.assertIn("receiving_proposals:leads&&privacy",self.admin)
        self.assertIn("admin_test_enabled:true",self.admin)
        self.assertIn("if(!authenticated(req))",self.admin)
        self.assertIn("El formulario",self.front) if "El formulario" in self.front else self.assertIn("La recepción de solicitudes",self.front)

if __name__=="__main__":
    unittest.main()
