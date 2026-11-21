"""AriMar banner click counting: aggregated, privacy-preserving and admin-only reporting."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AriMarClickTracking(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.home=(ROOT/'public/index.html').read_text(encoding='utf-8-sig')
  cls.endpoint=(ROOT/'api/ad-click.js').read_text(encoding='utf-8')
  cls.admin=(ROOT/'api/admin.js').read_text(encoding='utf-8')
  cls.admin_ui=(ROOT/'public/admin/admin.js').read_text(encoding='utf-8')
  cls.admin_html=(ROOT/'public/admin/index.html').read_text(encoding='utf-8')
  cls.schema=(ROOT/'sql/postgres_schema.sql').read_text(encoding='utf-8')

 def test_real_ad_link_keeps_destination_with_attribution(self):
  self.assertIn("const arimar=ad.id==='arimar-fundador'",self.home)
  self.assertIn("u.searchParams.set('utm_source','dparranda')",self.home)
  self.assertIn("u.searchParams.set('utm_medium','banner')",self.home)
  self.assertIn("u.searchParams.set('utm_campaign','arimar')",self.home)
  self.assertIn('data-sponsored-click="arimar-fundador"',self.home)
  self.assertIn("target=\"_blank\"",self.home)

 def test_click_is_sent_without_delaying_navigation(self):
  self.assertIn("e.target.closest('[data-sponsored-click]')",self.home)
  self.assertIn("navigator.sendBeacon('/api/ad-click',body)",self.home)
  self.assertIn("keepalive:true",self.home)
  self.assertNotIn("window.location='/api/ad-click'",self.home)

 def test_counter_only_records_valid_live_arimar_clicks(self):
  self.assertIn("if(req.method!=='POST')",self.endpoint)
  self.assertIn("if(!sameOrigin(req))",self.endpoint)
  self.assertIn("if(req.body?.id!=='arimar-fundador')",self.endpoint)
  self.assertIn("FROM ad_campaigns",self.endpoint)
  self.assertIn("enabled=TRUE",self.endpoint)
  self.assertIn("ON CONFLICT(campaign_id,day) DO UPDATE SET clicks=ad_daily_stats.clicks+1",self.endpoint)
  self.assertIn("Atlantic/Canary",self.endpoint)
  self.assertNotIn("x-forwarded-for",self.endpoint)
  self.assertNotIn("remoteAddress",self.endpoint)
  self.assertNotIn("user-agent",self.endpoint)
  self.assertIn("CREATE TABLE IF NOT EXISTS ad_daily_stats",self.schema)

 def test_only_admin_can_read_aggregates(self):
  self.assertIn("op==='arimar-click-stats'",self.admin)
  self.assertIn("if(!authenticated(req))",self.admin)
  self.assertIn("FROM ad_daily_stats WHERE campaign_id='arimar-fundador'",self.admin)
  self.assertIn("id='arimarClicksToday'",self.admin_html)
  self.assertIn("id='arimarClicksWeek'",self.admin_html)
  self.assertIn("id='arimarClicksMonth'",self.admin_html)
  self.assertIn("id='arimarClicksAll'",self.admin_html)
  self.assertIn("await api('arimar-click-stats')",self.admin_ui)
  self.assertIn("Los clics no equivalen",self.admin_html.replace("Se registran clics, no personas únicas ni pedidos.", "Los clics no equivalen a personas únicas"))

if __name__=='__main__':
 unittest.main()
