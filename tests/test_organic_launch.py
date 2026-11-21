"""Release contract: public organic launch preserves own ads and parks third-party sales."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class OrganicLaunchContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.home=(ROOT/"public/index.html").read_text(encoding="utf-8-sig")
  cls.robots=(ROOT/"public/robots.txt").read_text(encoding="utf-8")
  cls.sitemap=(ROOT/"public/sitemap.xml").read_text(encoding="utf-8")
  cls.vercel=json.loads((ROOT/"vercel.json").read_text(encoding="utf-8"))
  cls.flag=(ROOT/"lib/advertising-sales.js").read_text(encoding="utf-8")
  cls.intake=(ROOT/"api/advertise-interest.js").read_text(encoding="utf-8")
  cls.old_intake=(ROOT/"api/advertise.js").read_text(encoding="utf-8")
  cls.portal=(ROOT/"api/advertiser.js").read_text(encoding="utf-8")
  cls.stripe=(ROOT/"lib/stripe-advertising.js").read_text(encoding="utf-8")
  cls.admin=(ROOT/"api/admin.js").read_text(encoding="utf-8")
  cls.ads=(ROOT/"api/ads.js").read_text(encoding="utf-8")

 def test_home_becomes_crawlable_with_contact_and_sitemap(self):
  self.assertIn('content="index,follow,max-image-preview:large"',self.home)
  self.assertIn('rel="canonical" href="https://dparranda.es/"',self.home)
  self.assertIn('mailto:hola@dparranda.es',self.home)
  self.assertIn('Allow: /',self.robots)
  self.assertNotIn('Disallow: /\n',self.robots)
  self.assertIn('https://dparranda.es/sitemap.xml',self.robots)
  self.assertIn('<loc>https://dparranda.es/</loc>',self.sitemap)

 def test_organic_feed_keeps_real_house_campaigns_not_sales_placeholder(self):
  self.assertIn("function sponsorForSlot(slot)",self.home)
  self.assertIn("if(!active.length)return ''",self.home)
  self.assertIn("return sponsorCardHtml(active[slot%active.length])",self.home)
  self.assertNotIn("i===11?houseEventHtml()",self.home)
  self.assertIn("FROM ad_campaigns WHERE enabled=TRUE",self.ads)
  fallback=json.loads((ROOT/"public/ads.json").read_text(encoding="utf-8"))
  self.assertTrue(any(a["id"]=="arimar-fundador" and a["enabled"] for a in fallback["ads"]))

 def test_public_sales_pages_are_temporarily_redirected(self):
  routes=self.vercel["redirects"]
  for prefix in ("/anunciate","/anunciantes"):
   self.assertTrue(any(r["source"]==prefix and r["destination"]=="/" and r["permanent"] is False for r in routes))
   self.assertTrue(any(r["source"]==prefix+"/:path*" and r["destination"]=="/" and r["permanent"] is False for r in routes))

 def test_public_submission_and_payment_gate_default_closed(self):
  self.assertIn("process.env.DPARRANDA_ADVERTISING_SALES_ENABLED==='true'",self.flag)
  self.assertIn("advertisingSalesOpen()&&process.env.DPARRANDA_LEADS_ENABLED==='true'",self.intake)
  self.assertIn("advertisingSalesOpen()&&process.env.DPARRANDA_LEADS_ENABLED==='true'",self.old_intake)
  self.assertIn("if(!advertisingSalesOpen())return json(res,503",self.portal)
  self.assertIn("if(!advertisingSalesOpen())return {status:'sales_paused'}",self.stripe)
  self.assertIn("if(p.status==='sales_paused')",self.admin)

 def test_administration_and_commercial_source_retained(self):
  self.assertTrue((ROOT/"public/admin/index.html").exists())
  self.assertTrue((ROOT/"public/anunciate/index.html").exists())
  self.assertTrue((ROOT/"public/anunciantes/index.html").exists())
  self.assertTrue((ROOT/"lib/advertiser-mail.js").exists())
  self.assertTrue((ROOT/"api/stripe-webhook.js").exists())
  self.assertIn("op==='send-approved-payment'",self.admin)

if __name__=="__main__":
 unittest.main()
