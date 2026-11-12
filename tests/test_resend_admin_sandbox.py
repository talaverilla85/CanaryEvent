"""Resend sandbox integration never emails advertisers before a verified domain."""
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class ResendSandboxTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.mail=(R/'lib/resend-test.js').read_text('utf8')
  cls.admin=(R/'api/admin.js').read_text('utf8')
  cls.panel=(R/'public/admin/admin.js').read_text('utf8')
  cls.html=(R/'public/admin/index.html').read_text('utf8')
 def test_key_stays_on_server_and_is_opt_in(self):
  self.assertIn("process.env.RESEND_API_KEY",self.mail)
  self.assertIn("process.env.RESEND_TEST_RECIPIENT",self.mail)
  self.assertIn('https://api.resend.com/emails',self.mail)
  self.assertIn('onboarding@resend.dev',self.mail)
  self.assertIn('Idempotency-Key',self.mail)
  self.assertIn("export async function sendResendAdminTest()",self.mail)
  self.assertIn('customer_emails_enabled:false',self.admin)
  self.assertNotIn('process.env.RESEND_API_KEY',self.panel)
  self.assertNotIn('RESEND_API_KEY',self.html)
 def test_test_route_is_admin_only(self):
  self.assertLess(self.admin.index('if(!authenticated(req))'),self.admin.index("op==='resend-send-test'"))
  self.assertIn("req.method==='POST' && !sameOrigin(req)",self.admin)
  self.assertIn("op==='resend-test-config'",self.admin)
  self.assertIn("op==='resend-send-test'",self.admin)
  self.assertIn('id="sendResendTest"',self.html)
  self.assertIn('loadResendSandbox()',self.panel)
  self.assertIn("No se enviará nada a los anunciantes",self.panel)
 def test_validity_and_sandbox_limits(self):
  self.assertIn("response.status===403",self.mail)
  self.assertIn('Resend ha aceptado el correo',self.mail)
  self.assertIn('RESEND_TEST_RECIPIENT',self.panel)
  self.assertNotIn('advertiser_campaign_drafts',self.mail)
if __name__=='__main__':
 unittest.main()
