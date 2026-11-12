"""Stripe links are issued only after editorial approval and verified by signed webhook."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class StripeAdvertiserContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.engine=(ROOT/'lib/stripe-advertising.js').read_text('utf8')
  cls.webhook=(ROOT/'api/stripe-webhook.js').read_text('utf8')
  cls.mail=(ROOT/'lib/advertiser-mail.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.portal_ui=(ROOT/'public/anunciantes/portal.js').read_text('utf8')
  cls.admin_ui=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.schema=(ROOT/'sql/stripe_advertising.sql').read_text('utf8')
 def test_amounts_are_defined_server_side_for_30_and_60_days(self):
  for fragment in ('local:1900','zona:4900','insular:9900','[30,60].includes(Number(days))',
                   'STRIPE_PRICES[plan]*(Number(days)/30)'):
   self.assertIn(fragment,self.engine)
  self.assertIn("Number(d.price_cents)!==cents",self.engine)
  self.assertIn("'line_items[0][quantity]':'1'",self.engine)
 def test_payment_links_are_unique_and_created_only_from_approved_admin_drafts(self):
  for fragment in ('approved_for_payment','pending_payment','Idempotency-Key',
                   "'restrictions[completed_sessions][limit]':'1'",
                   'stripe_payment_link_id IS NULL','STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET'):
   self.assertIn(fragment,self.engine)
  self.assertIn("if(!authenticated(req))",self.admin)
  self.assertIn("safelyPreparePayment(sql,id)",self.admin)
  self.assertIn("send-approved-payment",self.admin)
  self.assertIn("data-ops-payment",self.admin_ui)
  self.assertIn("CREATE UNIQUE INDEX",self.schema)
 def test_signed_webhook_checks_exact_link_and_amount_before_marking_paid(self):
  for fragment in ("bodyParser:false","createHmac('sha256'","timingSafeEqual",
                  "checkout.session.completed","checkout.session.async_payment_succeeded",
                  "payment_link","expectedAmount(d.plan,d.days)","s.amount_total",
                  "payment_status='paid'","status='paid_review'",
                  "payment_status='pending'"):
   self.assertIn(fragment,self.webhook)
  self.assertNotIn("status='active'",self.webhook)
 def test_approved_and_paid_emails_and_private_payment_access(self):
  self.assertIn("sendPaymentApprovedEmail",self.mail)
  self.assertIn("sendPaymentConfirmedEmail",self.mail)
  self.assertIn("if(!canSendTo(info.account.email))",self.mail)
  self.assertIn("payment_url:d.status==='pending_payment'",self.portal)
  self.assertIn("Realizar pago seguro",self.portal_ui)
  self.assertIn("payment_status==='pending'",self.portal_ui)

if __name__=='__main__':unittest.main()
