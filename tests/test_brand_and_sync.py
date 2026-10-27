import unittest,json
from pathlib import Path
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"public/index.html").read_text(encoding="utf-8")
MANIFEST=json.loads((ROOT/"public/manifest.webmanifest").read_text(encoding="utf-8"))
WF=(ROOT/".github/workflows/sync-events.yml").read_text(encoding="utf-8")
SW=(ROOT/"public/sw.js").read_text(encoding="utf-8")

class BrandAndSyncContract(unittest.TestCase):
 def test_every_exposed_brand(self):
  self.assertIn("¿Pa' Dónde?",HTML)
  self.assertIn("¿Pa&#39; Dónde?",HTML)
  self.assertIn("¿Pa&#39; ",HTML)
  self.assertNotIn("<title>planGC",HTML)
  self.assertNotIn("planGC inicio",HTML)
  self.assertEqual(MANIFEST["short_name"],"Pa' Dónde")
 def test_favicon_and_pwa(self):
  r=ElementTree.parse(ROOT/"public/favicon.svg").getroot()
  self.assertEqual(r.tag,"{http://www.w3.org/2000/svg}svg")
  self.assertIn("padonde-flexible-filters-v2",SW)
  self.assertTrue((ROOT/"public/icons/icon-192.png").stat().st_size>1000)
 def test_sync_status_user_facing(self):
  self.assertIn("Última revisión:",HTML)
  self.assertIn("Revisión atrasada",HTML)
  self.assertIn("Atlantic/Canary",HTML)
  self.assertIn("fuente(s) con incidencias",HTML)
 def test_automatic_job_conflict_retry(self):
  self.assertIn("37 5 * * *",WF)
  self.assertIn("bash scripts/publish_synced_data.sh",WF)
  sh=(ROOT/"scripts/publish_synced_data.sh").read_text(encoding="utf-8")
  self.assertIn("git fetch --no-tags origin main",sh)
  self.assertIn("git reset --hard origin/main",sh)
  self.assertIn("python scripts/sync_events.py",sh)
  self.assertNotIn("git push --force",sh)
 def test_brand_plan_is_deferred_not_purchased(self):
  readme=(ROOT/"README.md").read_text(encoding="utf-8")
  self.assertIn("padondecanarias.es",readme)
  self.assertIn("OEPM",readme)
  self.assertIn("sin compras ni registros",readme)

if __name__=="__main__":unittest.main()


