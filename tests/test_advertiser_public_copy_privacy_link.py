"""Public advertiser confirmation must be friendly; legal notice must be accessible."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class AdvertiserPublicCopyContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.sim=(ROOT/"public/anunciate/simulador/simulator.js").read_text("utf8")
  cls.html=(ROOT/"public/anunciate/simulador/index.html").read_text("utf8")
  cls.mail=(ROOT/"lib/advertiser-mail.js").read_text("utf8")
  cls.form=(ROOT/"public/anunciate/form.js").read_text("utf8")
  cls.privacy=(ROOT/"public/privacidad/index.html").read_text("utf8")
  cls.api=(ROOT/"api/advertise-interest.js").read_text("utf8")
 def test_no_internal_request_number_in_public_confirmations(self):
  self.assertIn("¡Hemos recibido tu anuncio!",self.sim)
  self.assertIn("Tu prueba se ha guardado correctamente.",self.sim)
  self.assertNotIn("Solicitud #'+Number(result.request_id)",self.sim)
  self.assertNotIn("Solicitud '+data.request_id",self.form)
  self.assertIn("D’Parranda · Hemos recibido tu anuncio",self.mail)
  self.assertNotIn("solicitud #'+info.leadId",self.mail)
  self.assertIn("idempotencyKey:'dparranda-welcome-lead-'+info.leadId",self.mail)
  self.assertIn("request_id:Number(row.enquiry_id)",self.api)
 def test_privacy_readable_and_link_separate_from_consent(self):
  self.assertIn('id="interestPrivacy"',self.html)
  self.assertIn('href="/privacidad/"',self.html)
  self.assertIn('target="_blank" rel="noopener noreferrer"',self.html)
  self.assertIn('Leer la política de privacidad completa',self.html)
  self.assertIn('.interest-privacy-link a{color:',self.html)
  self.assertIn('.interest-privacy-link a:focus-visible',self.html)
  self.assertIn('<input name="consent" type="checkbox" required>',self.html)
  self.assertIn("('interestPrivacy').href=config.privacy_url",self.sim)
  self.assertIn("values.get('consent')==='on'",self.sim)
  self.assertIn('id="policy"',self.privacy)
  self.assertIn('id="legalName"',self.privacy)
  self.assertIn('id="rightsEmail"',self.privacy)
  self.assertNotIn('<label class="interest-consent"><input name="consent" type="checkbox" required><span>He leído la <a',self.html)
 def test_safeguards_for_payments_and_noindex_unchanged(self):
  self.assertIn("No se ha cobrado ni publicado nada.",self.sim)
  self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">',self.html)
  self.assertIn("const proposal=true",self.sim)
  self.assertIn("form.reportValidity()",self.sim)

if __name__=="__main__":
 unittest.main()
