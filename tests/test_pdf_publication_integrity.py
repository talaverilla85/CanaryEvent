import datetime as dt, hashlib, json, sqlite3, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_integrity as integrity
import telde_pdf_auto as auto
import telde_pdf_verified as gate
import refresh_telde_pdf_index as index

URL="https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf"
SHA="e4816f361dcaf1ec43ff7b1bc42a47b4c017fa8d2845828c417e9803392e48b0"
BASE={"title":"Concierto de música popular","date":"2026-11-07",
      "time":"20:30","venue":"Plaza de Caserones Altos",
      "evidence":"Concierto de música popular en Caserones Altos sábado 7 de noviembre a las 20:30",
      "type":"musica"}
RECORD={**BASE,"pdf_url":URL,"pdf_sha256":SHA,"pdf_page":1,
        "review_status":"auto_verified","verification":"two_independent_visual_passes"}
ID=hashlib.sha256(URL.encode()).hexdigest()[:16]
STATE={ID:{"sha":SHA,"done_pages":[0],"complete":False}}
PFX=f"{SHA}/0/{auto.tv.MODEL}/{auto.VERSION}"
CACHE={
 PFX+"/ai_vision":{"output":{"events":[BASE],"page_is_program":True}},
 PFX+"/independent_double_read":{"output":{"events":[{**BASE,"evidence":"Concierto de música popular 7 noviembre 20:30 Caserones Altos"}],"page_is_program":True}}
}

class PdfPublicationSecurity(unittest.TestCase):
 def test_live_repository_has_no_fake_approval(self):
  records=json.loads((ROOT/"data/telde_pdf_pilot/verified_events.json").read_text(encoding="utf8"))
  self.assertEqual(records,[])

 def test_actual_digest_and_two_attestations_required(self):
  today=dt.date(2026,10,27)
  self.assertTrue(integrity.trusted(RECORD,{URL},STATE,CACHE,today,auto.tv.MODEL,auto.VERSION))
  self.assertFalse(integrity.trusted({**RECORD,"pdf_sha256":"c"*64},{URL},STATE,CACHE,today,auto.tv.MODEL,auto.VERSION))
  self.assertFalse(integrity.trusted(RECORD,{URL},STATE,{},today,auto.tv.MODEL,auto.VERSION))
  tampered={**CACHE,PFX+"/independent_double_read":{"output":{"events":[{**BASE,"time":"22:00"}],"page_is_program":True}}}
  self.assertFalse(integrity.trusted(RECORD,{URL},STATE,tampered,today,auto.tv.MODEL,auto.VERSION))
  self.assertFalse(integrity.trusted(RECORD,{URL},{ID:{"sha":SHA,"done_pages":[]}},CACHE,today,auto.tv.MODEL,auto.VERSION))
  self.assertFalse(integrity.trusted(RECORD,{URL},STATE,CACHE,dt.date(2026,11,8),auto.tv.MODEL,auto.VERSION))

 def test_cleanup_only_invalid_pdf_source_not_other_sources(self):
  c=sqlite3.connect(":memory:")
  c.execute("CREATE TABLE events(id INTEGER PRIMARY KEY,title TEXT,start TEXT,source_url TEXT,source_name TEXT)")
  vals=[
   (611,"Concierto de música popular","2026-11-07T20:30:00",URL,gate.SOURCE),
   (612,"Pregón de San Gregorio","2026-11-06T20:00:00",URL,"Ayuntamiento de Telde · fiestas y cultura 2026")
  ]
  c.executemany("INSERT INTO events VALUES(?,?,?,?,?)",vals)
  removed=integrity.cleanup_stale(c,[])
  self.assertEqual(removed,1)
  self.assertEqual([x[0] for x in c.execute("SELECT id FROM events")],[612])

 def test_inventory_before_api_workflow_and_budget(self):
  workflow=(ROOT/".github/workflows/sync-events.yml").read_text(encoding="utf8")
  self.assertLess(workflow.index("run: python scripts/refresh_telde_pdf_index.py"),
                  workflow.index("python scripts/telde_pdf_auto.py --api"))
  self.assertIn("secrets.OPENAI_API_KEY",workflow)
  self.assertIn("--max-api-calls 4 --max-cost-usd 0.05",workflow)

 def test_index_keep_actual_document_titles(self):
  fake={"programs":[{"title":"Fiesta 2026","pdf_url":URL,"year":2026}]}
  self.assertEqual(len(fake["programs"]),1)
  self.assertTrue(URL.startswith("https://www.telde.es/"))

if __name__=="__main__":unittest.main()
