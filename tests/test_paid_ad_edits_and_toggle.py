"""Paid ad changes must not alter the purchased plan, price or contracted duration."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PaidAdManagementContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.logic=(ROOT/'lib/paid-ad-edit.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.advertiser=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.admin_ui=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.customer_ui=(ROOT/'public/anunciantes/portal.js').read_text('utf8')
  cls.image=(ROOT/'api/paid-event-image.js').read_text('utf8')
  cls.catalog=(ROOT/'api/catalog.js').read_text('utf8')

 def test_admin_only_paid_edits_and_no_contract_changes(self):
  self.assertIn("if(!authenticated(req))",self.admin)
  self.assertIn("op==='edit-paid-creative'",self.admin)
  self.assertIn("editPaidCreative(sql,data(req),adminImageData)",self.admin)
  self.assertIn("payment_status!=='paid'",self.logic)
  self.assertIn("!draft.stripe_checkout_session_id",self.logic)
  for protected in ("plan=","days=","price_cents=","campaign_start=","actual_starts_at=",
                    "actual_ends_at=","payment_status='pending'","stripe_checkout_session_id="):
   self.assertNotIn(protected,self.logic)
  self.assertIn("WHERE id=${id} AND payment_status='paid'",self.logic)
  self.assertIn("UPDATE sponsored_events",self.logic)
  self.assertIn("UPDATE ad_campaigns",self.logic)
  self.assertIn("advertiser_campaign_draft_images",self.logic)

 def test_pause_activate_requires_verified_payment_and_linked_publication(self):
  self.assertIn("op==='paid-ad-status'",self.admin)
  self.assertIn("setPaidPublicationEnabled(sql,data(req))",self.admin)
  self.assertIn("draft.payment_status!=='paid'||draft.status!=='active'",self.logic)
  self.assertIn("draft.ends_at<time.today",self.logic)
  self.assertIn("UPDATE sponsored_events SET enabled=${enabled}",self.logic)
  self.assertIn("UPDATE ad_campaigns SET enabled=${enabled}",self.logic)
  self.assertIn("WHERE id=${draft.published_event_id} AND advertiser_draft_id=${id}",self.logic)
  self.assertIn("AND kind='paid'",self.logic)
  self.assertIn("s.enabled=TRUE",self.image)
  self.assertIn("FROM sponsored_events WHERE enabled=TRUE",self.catalog)

 def test_admin_controls_and_customer_pause_status(self):
  for snippet in ("data-ops-paid-edit","data-ops-paid-toggle","edit-paid-creative",
                  "paid-ad-status","optimizePaidCreativeFile","openPaidCreativeEditor",
                  "handlePaidCampaignAction","'paused'"):
   self.assertIn(snippet,self.admin_ui)
  self.assertIn("published_enabled",self.admin)
  self.assertIn("published_enabled",self.advertiser)
  self.assertIn("const paused=d.status==='active'",self.customer_ui)
  self.assertIn("Campaña desactivada temporalmente",self.customer_ui)

if __name__=='__main__':unittest.main()
