"""Independent own-campaign duration versus paid-advertiser limits."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FlexibleHouseCampaigns(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.backend=(ROOT/'api/admin.js').read_text('utf-8')
  cls.panel=(ROOT/'public/admin/admin.js').read_text('utf-8')
  cls.html=(ROOT/'public/admin/index.html').read_text('utf-8')

 def test_no_sixty_day_limit_for_house_ads_only(self):
  self.assertIn("if(kind!=='house'&&duration>60)",self.backend)
  self.assertNotIn("if(duration<1||duration>60)",self.backend)
  self.assertIn("if(!Number.isSafeInteger(duration)||duration<1)",self.backend)
  self.assertIn("validLocalDate(starts)",self.backend)
  self.assertIn("validLocalDate(ends)",self.backend)
  self.assertIn("const enabled=body.enabled===true,permanent=false",self.backend)

 def test_admin_can_enter_days_and_see_expiry_calculated(self):
  self.assertIn('id="f-duration_days"',self.panel)
  self.assertIn('type="number" min="1" step="1" required',self.panel)
  self.assertIn('name="ends_at" type="date" readonly',self.panel)
  self.assertIn("function campaignEndFromDays(start,days)",self.panel)
  self.assertIn("const end=campaignEndFromDays($('f-starts_at').value,$('f-duration_days').value)",self.panel)
  self.assertIn("f.ends_at=campaignEndFromDays(f.starts_at,f.duration_days)",self.panel)
  self.assertIn("delete f.duration_days",self.panel)
  self.assertIn("Las campañas antiguas sin caducidad",self.panel)

 def test_admin_shows_expiry_and_days_remaining_even_if_paused(self):
  self.assertIn("' · Caduca: '+(ended?formatCampaignDate(ended)",self.panel)
  self.assertIn("function daysLeft(value)",self.panel)
  self.assertIn("r.actual_ends_at&&r.source==='house'",self.panel)
  self.assertIn("'<small>Caduca: '+escape(formatCampaignDate(r.actual_ends_at))",self.panel)
  self.assertIn("escape(daysLeft(r.actual_ends_at))",self.panel)
  self.assertIn("<th>Días / caducidad</th>",self.html)
  self.assertNotIn("Los nuevos anuncios tienen un máximo de 60 días",self.html)

 def test_permanent_arimar_is_not_migrated_until_saved(self):
  self.assertIn("const startDefault=ad.permanent?today:",self.panel)
  self.assertIn("const existingEnd=ad.permanent?'':",self.panel)
  self.assertIn("f.permanent=false;f.kind='house'",self.panel)

if __name__=='__main__':
 unittest.main()
