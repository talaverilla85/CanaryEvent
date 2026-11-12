"""Regression contracts for automatic Stripe scheduling and multiple free house campaigns."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class OwnAdvertisingAndScheduling(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.webhook=(ROOT/'api/stripe-webhook.js').read_text('utf8')
  cls.panel=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.html=(ROOT/'public/admin/index.html').read_text('utf8')
  cls.image=(ROOT/'api/ad-image.js').read_text('utf8')
  cls.public=(ROOT/'public/index.html').read_text('utf8')
  cls.public_ads=(ROOT/'api/ads.js').read_text('utf8')
 def test_own_ad_creation_is_free_and_admin_only(self):
  self.assertIn('id="createOwnAd"',self.html)
  self.assertIn("'createOwnAd').onclick=()=>editAd(null)",self.panel)
  self.assertIn("kind:'house'",self.panel)
  self.assertIn("f.kind='house'",self.panel)
  self.assertIn("payment:'free'",self.panel)
  self.assertIn("price:0",self.panel)
  self.assertIn("if(!authenticated(req))",self.admin)
  self.assertIn("kind!==kind",self.admin)
  self.assertIn("duration>60",self.admin)
 def test_campaigns_can_be_created_edited_paused_independently(self):
  for fragment in ("data-ops-house-edit","data-ops-house-toggle",
                   "house-ad-status","handleOwnCampaignAction",
                   "if(a.kind==='house')","f.image_data=encoded",
                   "const id=typeof body.id"):
   self.assertIn(fragment,self.panel if fragment!="const id=typeof body.id" else self.admin)
  self.assertIn("op==='house-ad-status'",self.admin)
  self.assertIn("WHERE id=${id} AND kind='house'",self.admin)
 def test_uploaded_public_images_require_valid_active_campaign_dates(self):
  for fragment in ("ad.enabled=TRUE","ad.kind='house'","s-maxage=120",
                   "ad.starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date)",
                   "ad.ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)"):
   self.assertIn(fragment,self.image)
  self.assertIn("ad-image",self.public)
  self.assertIn("'/api/ad-image?id='",self.public_ads)
 def test_verified_payment_schedules_without_admin_click(self):
  for fragment in ("'checkout.session.completed'","schedulePaidDraft(sql,Number(confirmedId))",
                   "d.payment_status==='paid'","return res.status(503)"):
   self.assertIn(fragment,self.webhook)
  self.assertIn("await schedulePaidDraft(sql,Number(confirmedId))",self.webhook)

if __name__=='__main__':unittest.main()
