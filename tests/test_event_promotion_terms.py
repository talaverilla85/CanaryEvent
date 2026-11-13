"""The fixed promotion period is disclosed for sponsored events before submission and payment."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class EventPromotionTermsContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.landing=(ROOT/'public/anunciate/index.html').read_text('utf8')
  cls.sim=(ROOT/'public/anunciate/simulador/index.html').read_text('utf8')
  cls.sim_js=(ROOT/'public/anunciate/simulador/simulator.js').read_text('utf8')
  cls.portal=(ROOT/'public/anunciantes/index.html').read_text('utf8')
  cls.workspaces=(ROOT/'lib/advertiser-workspace.js').read_text('utf8')
  cls.mail=(ROOT/'lib/advertiser-mail.js').read_text('utf8')
  cls.catalog=(ROOT/'api/catalog.js').read_text('utf8')
  cls.image=(ROOT/'api/paid-event-image.js').read_text('utf8')

 def test_clear_notice_in_all_advertiser_entry_points(self):
  self.assertIn('no se amplía ni se ajusta automáticamente',self.landing)
  self.assertIn('no se amplía ni se ajusta automáticamente',self.sim)
  self.assertIn('no se amplía ni ajusta automáticamente',self.portal)
  self.assertIn('id="eventCampaignRule"',self.sim)
  self.assertIn("eventCampaignRule').hidden=draft.kind!=='evento'",self.sim_js)
  self.assertIn("landing.js?v=6",self.landing)
  self.assertIn("simulator.js?v=9",self.sim)

 def test_pre_payment_mail_is_specific_to_events(self):
  self.assertIn("info.draft?.placement==='evento'",self.mail)
  self.assertIn("Conviene contratar con suficiente antelación.",self.mail)
  self.assertIn("d.title,d.status,d.placement",self.workspaces)
  self.assertIn("status:draft.status,placement",self.workspaces)
  self.assertIn("status:row.status,placement:row.placement",self.workspaces)

 def test_expired_event_is_hidden_without_extending_paid_period(self):
  self.assertIn('left(COALESCE(NULLIF("end",\'\'),start),10)',self.catalog)
  self.assertIn('left(COALESCE(NULLIF(s."end",\'\'),s.start),10)',self.image)

if __name__=='__main__':
 unittest.main()
