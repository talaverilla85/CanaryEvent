import datetime as dt
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import telde_pdf_vision as tv

class PdfVisionPilotTests(unittest.TestCase):
 def test_secure_official_source_only(self):
  good="https://www.telde.es/wp-content/uploads/2026/09/sanfrancisco26.pdf"
  self.assertEqual(tv.verify_pdf_url(good,2026),good)
  for bad in (
   "http://www.telde.es/wp-content/uploads/2026/09/sanfrancisco26.pdf",
   "https://evil.example/wp-content/uploads/2026/09/sanfrancisco26.pdf",
   "https://www.telde.es/wp-content/uploads/2026/09/../../../../secret.pdf",
   "https://www.telde.es/wp-content/uploads/2025/09/sanfrancisco26.pdf",
   "https://www.telde.es/admin/database.pdf",
   "https://www.telde.es/wp-content/uploads/2026/09/fake.pdf?x=1",
  ):
   with self.subTest(bad=bad),self.assertRaises(ValueError):tv.verify_pdf_url(bad,2026)

 def test_selects_only_indexed_files_and_bounds(self):
  docs=[{"pdf_url":f"https://www.telde.es/wp-content/uploads/2026/{m:02d}/thing{m}.pdf","year":2026}
        for m in [1,2,3]]
  self.assertEqual(tv.select_programs({"programs":docs},None,1)[0]["year"],2026)
  self.assertEqual(len(tv.select_programs({"programs":docs},None,2)),2)
  with self.assertRaises(ValueError):tv.select_programs({"programs":docs},"invented.pdf",1)

 def test_past_program_never_approved_or_published(self):
  o=dict(title="Concierto de Covi Quintana",date="2026-10-04",time="20:30",
         venue="Plaza de San Francisco",evidence="04 Oct 20:30 h Concierto de Covi Quintana",type="musica")
  v,error=tv.validate_candidate(o,2026,"Fiestas San Francisco", "https://www.telde.es/wp-content/uploads/2026/09/sanfrancisco26.pdf",
    "b"*64,0,dt.date(2026,10,26))
  self.assertIsNone(error)
  self.assertEqual(v["date_state"],"expired")
  self.assertEqual(v["review_status"],"pending_review")
  self.assertEqual(v["pdf_page"],1)
  self.assertEqual(v["municipality"],"Telde")
  self.assertNotIn("status",v)

 def test_unsubstantiated_claims_rejected(self):
  base=dict(title="Concierto de Covi Quintana",date="2026-10-04",time="20:30",
            venue="Plaza de San Francisco",evidence="04 Oct 20:30 h Concierto de Covi Quintana",type="musica")
  tests=[("date","2027-10-04"),("date","04/10/26"),("date","2026-13-04"),
         ("time","26:90"),("title","Feria"),("evidence","x"),("type","crimen")]
  for field,value in tests:
   test={**base,field:value}
   with self.subTest(field=field,value=value):
    v,error=tv.validate_candidate(test,2026,"program","https://www.telde.es/official.pdf","x",0,dt.date(2026,10,26))
    self.assertIsNone(v)
    self.assertIsNotNone(error)

 def test_null_time_and_location_accepted_as_unverified(self):
  x=dict(title="Actividad infantil en el barrio",date="2026-11-02",time=None,venue=None,
         evidence="2 noviembre · actividad infantil en el barrio",type="familia")
  v,error=tv.validate_candidate(x,2026,"program","https://www.telde.es/pdf", "x"*64,0,dt.date(2026,10,26))
  self.assertIsNone(error)
  self.assertIsNone(v["time"])
  self.assertIsNone(v["venue"])
  self.assertEqual(v["date_state"],"upcoming")

 def test_price_usage_excluding_cached_input(self):
  usage={"input_tokens":2100,"output_tokens":600,"input_tokens_details":{"cached_tokens":1000}}
  expected=(1100*.10+1000*.01+600*.50)/1e6
  self.assertAlmostEqual(tv.response_usage_cost(usage),round(expected,7))

 def test_model_schema_strict_and_nostore(self):
  class Response:
   status_code=200
   def json(self):
    return {"status":"completed","output":[{"type":"message",
       "content":[{"type":"output_text","text":json.dumps({"events":[],"page_is_program":False})}]}],
       "usage":{"input_tokens":400,"output_tokens":100}}
  class Fake:
   payload=None
   def post(self,url,headers,json,timeout):
    self.payload=json
    self.url=url
    self.headers=headers
    return Response()
  f=Fake()
  decoded,usage=tv.call_openai_vision(b"fake-jpg",2026,"Fiestas",tv.MODEL,"fake-example-key",f)
  self.assertEqual(decoded,{"events":[],"page_is_program":False})
  self.assertEqual(f.url,"https://api.openai.com/v1/responses")
  self.assertFalse(f.payload["store"])
  self.assertEqual(f.payload["text"]["format"]["type"],"json_schema")
  self.assertTrue(f.payload["text"]["format"]["strict"])
  self.assertTrue(f.payload["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,"))
  self.assertEqual(usage["output_tokens"],100)

 def test_http_error_does_not_log_key_or_retry(self):
  class Response:
   status_code=401
   def json(self):return {"error":{"type":"invalid_api_key"}}
  class Fake:
   attempts=0
   def post(self,*args,**kwargs):self.attempts+=1;return Response()
  f=Fake()
  with self.assertRaises(RuntimeError) as cm:
   tv.call_openai_vision(b"jpg",2026,"Fiestas",tv.MODEL,"do-not-leak",f)
  self.assertEqual(f.attempts,1)
  self.assertNotIn("do-not-leak",str(cm.exception))

 def test_no_api_is_zero_spend_without_openai_key(self):
  self.assertFalse("--api" in ["--filename","sanfrancisco26.pdf","--max-pages","1"])
  self.assertEqual(tv.REVIEW.parent,tv.ROOT/"data"/"telde_pdf_pilot")

if __name__=="__main__":unittest.main()
