import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/"data/island_sources.json").read_text(encoding="utf8"))
class CanaryCoveragePlanTests(unittest.TestCase):
 def test_eight_islands_and_88_municipalities(self):
  rows=SOURCE["islands"]
  self.assertEqual(len(rows),8)
  self.assertEqual(len({r["name"] for r in rows}),8)
  self.assertEqual(sum(r["municipalities"] for r in rows),88)
  self.assertEqual(next(x for x in rows if x["name"]=="La Graciosa")["parent_municipality"],"Teguise")
 def test_no_false_coverage(self):
  active=[x["name"] for x in SOURCE["islands"] if x["status"]=="active"]
  self.assertEqual(active,["Gran Canaria"])
  self.assertTrue(all(x["seed_sources"] for x in SOURCE["islands"]))
 def test_realistic_integration_requirements(self):
  requirements=" ".join(SOURCE["requirements_before_public_activation"])
  self.assertIn("SQLite",requirements)
  self.assertIn("island selector",requirements.lower())
  self.assertIn("No empty island",requirements)

if __name__=="__main__":unittest.main()
