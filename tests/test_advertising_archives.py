"""Self-service archive is reversible, protected and cannot publish or erase paid contracts."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class AdvertisingArchiveContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.logic=(ROOT/'lib/advertising-archive.js').read_text('utf8')
  cls.sql=(ROOT/'sql/advertising-archives.sql').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.ui=(ROOT/'public/admin/admin.js').read_text('utf8')
  cls.html=(ROOT/'public/admin/index.html').read_text('utf8')
  cls.stripe=(ROOT/'lib/stripe-advertising.js').read_text('utf8')
  cls.webhook=(ROOT/'api/stripe-webhook.js').read_text('utf8')
  cls.scheduler=(ROOT/'lib/advertiser-publication.js').read_text('utf8')
  cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.public_ads=(ROOT/'api/ads.js').read_text('utf8')
  cls.catalog=(ROOT/'api/catalog.js').read_text('utf8')
  cls.image=(ROOT/'api/paid-event-image.js').read_text('utf8')

 def test_admin_only_and_confirmation(self):
  self.assertIn('if(!authenticated(req))',self.admin)
  self.assertIn("op==='advertising-archives'",self.admin)
  self.assertIn("op==='advertising-archive'",self.admin)
  self.assertIn("changeAdvertisingArchive(sql,data(req))",self.admin)
  self.assertIn('if(req.method===\'POST\' && !sameOrigin(req))',self.admin)
  self.assertIn("archiving?'ARCHIVAR':'RESTAURAR'",self.logic)
  self.assertIn("confirmation:word",self.ui)
  self.assertIn("Escribe '+word+' para confirmar",self.ui)

 def test_archiving_is_non_destructive_and_founder_protected(self):
  self.assertIn('CREATE TABLE IF NOT EXISTS advertising_archives',self.sql)
  self.assertIn('PRIMARY KEY(source,record_id)',self.sql)
  self.assertNotIn('DELETE FROM advertiser_campaign_drafts',self.logic)
  self.assertNotIn('DELETE FROM advertising_enquiries',self.logic)
  self.assertNotIn('DELETE FROM ad_campaigns',self.logic)
  self.assertIn("recordId==='arimar-fundador'",self.logic)
  self.assertIn("UPDATE sponsored_events SET enabled=FALSE",self.logic)
  self.assertIn("UPDATE ad_campaigns SET enabled=FALSE",self.logic)
  self.assertIn("DELETE FROM advertising_archives",self.logic)
  self.assertIn("La publicación no se reactiva automáticamente",self.logic)

 def test_stripe_links_are_safely_handled(self):
  self.assertIn("https://api.stripe.com/v1/payment_links/",self.logic)
  self.assertIn("await updateStripeLink(draft.stripe_payment_link_id,false)",self.logic)
  self.assertIn("await updateStripeLink(draft.stripe_payment_link_id,true)",self.logic)
  self.assertIn("result.active!==active",self.logic)
  self.assertIn("STRIPE_SECRET_KEY",self.logic)
  self.assertIn("advertising_archives",self.stripe)
  self.assertIn("d.archived",self.webhook)
  self.assertIn("advertising_archives",self.scheduler)

 def test_public_visibility_excludes_archived(self):
  for src in (self.public_ads,self.catalog,self.image,self.portal):
   self.assertIn('advertising_archives',src)
  self.assertIn("if(opsFilter==='archived')",self.ui)
  self.assertIn("opsAllRows.filter(r=>!r.archived",self.ui)
  self.assertIn("data-ops-archive",self.ui)
  self.assertIn("data-ops-restore",self.ui)
  self.assertIn("function isArchived(source,id)",self.ui)
  self.assertIn("const visibleAds=ads.filter",self.ui)
  self.assertIn("const visibleLeads=leads.filter",self.ui)
  self.assertIn("Archivados · recuperables",self.html)
  self.assertIn("No se reactivará",self.ui.replace("no se reactivará","No se reactivará"))

if __name__=='__main__':
 unittest.main()
