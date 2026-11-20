"""Pago: un fallo de Resend no debe ocultar el enlace Stripe al administrador."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PaymentEmailFallbackContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.stripe=(ROOT/"lib/stripe-advertising.js").read_text("utf8")
  cls.mail=(ROOT/"lib/advertiser-mail.js").read_text("utf8")
  cls.admin=(ROOT/"api/admin.js").read_text("utf8")
  cls.ui=(ROOT/"public/admin/admin.js").read_text("utf8")
  cls.portal=(ROOT/"api/advertiser.js").read_text("utf8")

 def test_existing_link_is_reused(self):
  self.assertIn("let link={id:d.stripe_payment_link_id,url:d.stripe_payment_url}",self.stripe)
  self.assertIn("if(!link.id||!link.url)",self.stripe)
  self.assertIn("return {status:'ready',email_status:email.status,url:link.url",self.stripe)
  self.assertIn("status:'email_unavailable',url:link.url",self.stripe)

 def test_explicit_resend_uses_unique_attempt_and_same_link(self):
  self.assertIn("ensureApprovedPayment(sql,id,{retryKey})",self.admin)
  self.assertIn("safeText(data(req).attempt_key,64)",self.admin)
  self.assertIn("sendPaymentApprovedEmail(workspace,link.url,cents,d.plan,d.days,link.id,{retryKey})",self.stripe)
  self.assertIn("'-retry-'+String(retryKey)",self.mail)
  self.assertIn("crypto.randomUUID().replaceAll('-','')",self.ui)

 def test_admin_receives_and_displays_payment_link(self):
  self.assertIn("payment_url:payment?.url||null",self.admin)
  self.assertIn("showApprovedPaymentLink(result)",self.ui)
  self.assertIn("id=\"copyApprovedPaymentLink\"",self.ui)
  self.assertIn("u.hostname==='buy.stripe.com'",self.ui)
  self.assertIn("navigator.clipboard.writeText(area.value)",self.ui)
  self.assertIn("Resend no pudo enviar el correo",self.ui)

 def test_advertiser_portal_still_offers_payment_link(self):
  self.assertIn("payment_url:d.status==='pending_payment'",self.portal)
  self.assertIn("d.payment_status==='pending'",self.portal)

if __name__=="__main__":
 unittest.main()
