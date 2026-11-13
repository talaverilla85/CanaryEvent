"""A confirmed Stripe payment creates only a reversible administrative review item."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class InvoiceReviewContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.schema=(ROOT/'sql/advertising-invoice-reviews.sql').read_text('utf8')
  cls.logic=(ROOT/'lib/advertising-invoice-reviews.js').read_text('utf8')
  cls.webhook=(ROOT/'api/stripe-webhook.js').read_text('utf8')
  cls.payment=(ROOT/'lib/stripe-advertising.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.panel=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.html=(ROOT/'public/admin/index.html').read_text('utf8')

 def test_queue_is_tied_to_verified_stripe_payment_and_idempotent(self):
  self.assertIn('PRIMARY KEY REFERENCES',self.schema.replace('PRIMARY KEY REFERENCES','PRIMARY KEY REFERENCES'))
  self.assertIn('stripe_checkout_session_id TEXT NOT NULL UNIQUE',self.schema)
  self.assertIn("review_status TEXT NOT NULL DEFAULT 'pending'",self.schema)
  self.assertIn("ON CONFLICT(draft_id) DO NOTHING",self.logic)
  self.assertIn("d.payment_status='paid'",self.logic)
  self.assertIn("d.stripe_checkout_session_id=",self.logic)
  self.assertIn('prepareInvoiceReview(sql,Number(confirmedId),s)',self.webhook)
  self.assertIn("if(confirmedId)await prepareInvoiceReview",self.webhook)

 def test_stripe_collects_billing_but_does_not_generate_second_invoice(self):
  self.assertIn("'billing_address_collection':'required'",self.payment)
  self.assertIn("'tax_id_collection[enabled]':'true'",self.payment)
  self.assertIn("'invoice_creation[enabled]':'false'",self.payment)
  self.assertIn('metadata[dparranda_draft_id]',self.payment)

 def test_admin_views_are_authenticated_and_not_shared_publicly(self):
  self.assertIn("if(!authenticated(req))return json",self.admin)
  self.assertIn("op==='invoice-reviews'",self.admin)
  self.assertIn("op==='invoice-review-preview'",self.admin)
  self.assertIn("op==='invoice-review-update'",self.admin)
  self.assertIn("frame-ancestors 'none'",self.admin)
  self.assertIn('invoiceReviewPanel',self.html)
  self.assertIn('invoiceReviewsList',self.html)
  self.assertIn("loadInvoiceReviews()",self.panel)
  self.assertIn("invoice-review-update",self.panel)

 def test_preview_cannot_be_mistaken_for_an_issued_invoice(self):
  self.assertIn('BORRADOR INTERNO · NO ES FACTURA',self.logic)
  self.assertIn('NO ENVIAR',self.logic)
  self.assertIn('SIN VALIDEZ FISCAL',self.logic)
  self.assertIn('No se envía ni expide documentación fiscal',self.logic)
  self.assertIn('legal_invoice_emission:false',self.logic)
  self.assertIn('sent:false',self.logic)
  self.assertNotIn('invoice_number',self.schema)
  self.assertNotIn('sendInvoiceEmail',self.logic)

if __name__=='__main__': unittest.main()
