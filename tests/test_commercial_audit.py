"""Regression contracts for checkout copy, archive security and sponsored event dates."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CommercialAuditContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.intake=(ROOT/'api/advertise-interest.js').read_text('utf8')
  cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.portal_ui=(ROOT/'public/anunciantes/portal.js').read_text('utf8')
  cls.portal_html=(ROOT/'public/anunciantes/index.html').read_text('utf8')
  cls.stripe=(ROOT/'lib/stripe-advertising.js').read_text('utf8')
  cls.mail=(ROOT/'lib/advertiser-mail.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
  cls.catalog=(ROOT/'api/catalog.js').read_text('utf8')
  cls.image=(ROOT/'api/paid-event-image.js').read_text('utf8')
  cls.tests=(ROOT/'tests/test_commercial_workflow.mjs').read_text('utf8')

 def test_archived_campaign_cannot_be_edited_from_stale_browser_session(self):
  self.assertIn("advertising_archives ar WHERE ar.source='draft'",self.portal)
  self.assertIn("ar.record_id=advertiser_campaign_drafts.id::text",self.portal)
  self.assertIn("status IN ('draft','changes_requested')",self.portal)
  self.assertIn("if(!r)return json(res,409",self.portal)

 def test_advertiser_private_area_never_shows_internal_identifiers(self):
  self.assertNotIn("'Editar borrador #'+d.id",self.portal_ui)
  self.assertNotIn("'Borrador #'+result.id",self.portal_ui)
  self.assertIn("'Editar mi anuncio'",self.portal_ui)
  self.assertIn('portal.js?v=3',self.portal_html)

 def test_checkout_has_no_visible_internal_request_id(self):
  self.assertIn("'line_items[0][price_data][product_data][description]':String(d.title).slice(0,120)",self.stripe)
  self.assertNotIn("'Anuncio #'+d.id",self.stripe)
  self.assertIn("'metadata[dparranda_draft_id]':String(d.id)",self.stripe)
  self.assertIn("expectedAmount(d.plan,d.days)",self.stripe)
  self.assertIn("Idempotency-Key",self.stripe)
  self.assertIn("if(d.payment_status==='paid')",self.stripe)

 def test_only_future_relevant_sponsored_events_are_available_for_sale_and_discovery(self):
  self.assertIn("eventDate.slice(0,10)<todayCanary()",self.intake)
  self.assertIn("eventDate.slice(0,10)<start",self.intake)
  self.assertIn("eventStart.slice(0,10)<today()",self.portal)
  self.assertIn("eventStart.slice(0,10)<start",self.portal)
  self.assertIn("eventDay<canaryDate()",self.stripe)
  self.assertIn("eventDay<d.campaign_start_iso",self.stripe)
  self.assertIn("lead.event_start.slice(0,10)<canaryToday()",self.admin)
  self.assertIn("draft.event_start.slice(0,10)<canaryToday()",self.admin)
  self.assertIn("COALESCE(NULLIF(\"end\",''),start)",self.catalog)
  self.assertIn("COALESCE(NULLIF(s.\"end\",''),s.start)",self.image)

 def test_payment_confirmed_copy_is_consistent_with_auto_scheduling(self):
  self.assertIn("Hemos registrado tu contratación y preparado la programación",self.mail)
  self.assertNotIn("Tu contratación está registrada y queda pendiente de su publicación",self.mail)
  self.assertIn("Puedes consultar las fechas y el estado de tu campaña",self.mail)
  self.assertIn("No se ha realizado ningún cobro ni se ha publicado el anuncio.",self.mail)
  self.assertIn("Deactivación",self.tests.replace("Desactivación","Deactivación"))

if __name__=="__main__":unittest.main()
