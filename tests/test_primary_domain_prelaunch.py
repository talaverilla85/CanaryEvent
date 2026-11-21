"""Primary domain is .es; the homepage is indexable during organic launch."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PrimaryDomainContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.mail=(ROOT/'lib/advertiser-mail.js').read_text('utf8')
  cls.privacy=(ROOT/'lib/privacy.js').read_text('utf8')
  cls.robots=(ROOT/'public/robots.txt').read_text('utf8')
  cls.home=(ROOT/'public/index.html').read_text('utf8')
 def test_advertiser_links_use_primary_domain(self):
  self.assertIn("https://dparranda.es/anunciantes/#acceso=",self.mail)
  self.assertNotIn("canaryevent.vercel.app",self.mail)
 def test_legal_links_use_primary_domain(self):
  self.assertIn("https://dparranda.es/privacidad/",self.privacy)
  self.assertNotIn("canaryevent.vercel.app",self.privacy)
 def test_home_is_indexable_and_commercial_paths_not_crawlable(self):
  self.assertIn('Allow: /',self.robots)
  self.assertNotIn('Disallow: /\n',self.robots)
  self.assertIn('Disallow: /anunciate/',self.robots)
  self.assertIn('content="index,follow,max-image-preview:large"',self.home)
  self.assertIn('href="https://dparranda.es/"',self.home)
 def test_resend_stays_in_sandbox_until_verified(self):
  self.assertIn("RESEND_CUSTOMER_EMAILS_ENABLED==='true'",self.mail)
  self.assertIn("RESEND_TEST_RECIPIENT",self.mail)
  self.assertIn("onboarding@resend.dev",self.mail)

if __name__=='__main__':unittest.main()
