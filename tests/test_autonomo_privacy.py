"""Privacy/legal identity guard for an autónomo running DParranda."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AutonomoPrivacyContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.privacy=(ROOT/'lib/privacy.js').read_text('utf8')
  cls.api=(ROOT/'api/privacy.js').read_text('utf8')
  cls.html=(ROOT/'public/privacidad/index.html').read_text('utf8')
  cls.js=(ROOT/'public/privacidad/privacidad.js').read_text('utf8')
  cls.leads=(ROOT/'api/advertise-interest.js').read_text('utf8')
  cls.portal=(ROOT/'api/advertiser.js').read_text('utf8')
  cls.admin=(ROOT/'api/admin.js').read_text('utf8')
 def test_complete_identity_is_required_before_real_intake(self):
  for key in ('DPARRANDA_LEGAL_NAME','DPARRANDA_LEGAL_ADDRESS','DPARRANDA_LEGAL_NIF','DPARRANDA_PRIVACY_EMAIL'):
   self.assertIn(key,self.privacy)
  self.assertIn('if(missingPrivacyIdentity().length)return null',self.privacy)
  self.assertIn("if(!publicPrivacyDetails())return null",self.privacy)
  self.assertIn("DPARRANDA_LEADS_ENABLED",self.leads)
  self.assertIn("!!privacyUrl()",self.leads)
  self.assertIn('legalPrivacyUrl()',self.portal)
  self.assertIn('missing_legal_fields:missingPrivacyIdentity()',self.admin)
  self.assertIn("admin_test_enabled:true",self.admin)
 def test_privacy_not_published_with_fake_or_partial_identity(self):
  self.assertIn("if(!identity)return json(res,200,{ready:false})",self.api)
  self.assertIn("if(info?.ready!==true)",self.js)
  self.assertIn("$('unavailable').hidden=false",self.js)
  for key in ("legal_name","legal_address","legal_nif","privacy_email"):
   self.assertIn(key,self.js)
  self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">',self.html)
  self.assertIn('id="rightsEmail"',self.html)
  self.assertIn('artículo 6.1.b',self.html)
  self.assertIn('Agencia Española de Protección de Datos',self.html)
 def test_no_new_payment(self):
  self.assertIn('payment_enabled:false',self.leads)
  self.assertIn('accepting_payments:false',self.admin)
  self.assertNotIn('checkout.sessions.create',self.leads)
if __name__=='__main__':
 unittest.main()
