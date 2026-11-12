"""Paid advertising publication is admin-only, date limited, and previewable."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdvertisingPaidPublicationContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.logic=(ROOT/'lib/advertiser-publication.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.panel=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.panel_css=(ROOT/'public/admin/admin.css').read_text('utf8')
  cls.catalog=(ROOT/'api/catalog.js').read_text('utf8')
  cls.ads=(ROOT/'api/ads.js').read_text('utf8')
  cls.event_image=(ROOT/'api/paid-event-image.js').read_text('utf8')
  cls.banner_image=(ROOT/'api/paid-banner-image.js').read_text('utf8')
  cls.public=(ROOT/'public/index.html').read_text('utf8')
  cls.portal=(ROOT/'public/anunciantes/portal.js').read_text('utf8')
  cls.sql=(ROOT/'sql/advertiser-publication.sql').read_text('utf8')

 def test_manual_publication_only_after_stripe_confirmation(self):
  for check in ("d.payment_status!=='paid'","!d.paid_at","!d.stripe_checkout_session_id",
                "expectedAmount(d.plan,d.days)","['paid_review','approved','active'].includes(d.status)",
                "status='approved'","status='active'"):
   self.assertIn(check,self.logic)
  self.assertIn("if(!authenticated(req))",self.admin)
  self.assertIn("op==='schedule-paid-draft'",self.admin)
  self.assertIn("schedulePaidDraft(sql,id)",self.admin)
  self.assertIn("data-ops-schedule",self.panel)
  self.assertIn("if(!confirm('¿Programar",self.panel)

 def test_date_scoped_publication_without_cron_or_backdating(self):
  self.assertIn("timeZone:'Atlantic/Canary'",self.logic)
  self.assertIn("canaryToday()?canaryToday():start",self.logic)
  self.assertIn("(days-1)*86400000",self.logic)
  for snippet in ("campaign_starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date)",
                  "campaign_ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)"):
   self.assertIn(snippet,self.catalog)
  for snippet in ("starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date)",
                  "ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)"):
   self.assertIn(snippet,self.ads)
  self.assertIn("const scheduled=d.status==='active'",self.portal)

 def test_public_images_require_active_paid_ad(self):
  for endpoint in (self.event_image,self.banner_image):
   self.assertIn("d.payment_status='paid'",endpoint)
   self.assertIn("d.status='active'",endpoint)
   self.assertIn("s-maxage=120",endpoint)
  self.assertIn("paid-event-image?id=",self.catalog)
  self.assertIn("paid-banner-image?id=",self.ads)
  self.assertIn("paid-event-image",self.public)
  self.assertIn("paid-banner-image",self.public)
  self.assertIn("advertiser_draft_id",self.sql)
  self.assertIn("CREATE UNIQUE INDEX",self.sql)

 def test_preview_does_not_publish(self):
  self.assertIn('adops-live-card',self.panel_css)
  self.assertIn('Vista previa de la tarjeta en D’Parranda',self.panel)
  self.assertIn('No implica publicación',self.panel)
  self.assertIn("row.event_town",self.panel)
  self.assertIn("schedule-paid-draft",self.panel)
  self.assertIn("row.status==='paid_review'",self.panel)

if __name__=='__main__':unittest.main()
