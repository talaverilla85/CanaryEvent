import datetime as dt,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import galdar_agenda as g
import sync_events as s

def row(start="2026-11-07T20:00+1:00",end="2026-11-07T22:00+1:00",url="https://www.galdar.es/events/conversaciones-con-mi-mente-joaquin-caserza/"):
 return '''<div class="eventon_list_event" itemtype="http://schema.org/Event">
 <div class="evo_event_schema">
 <a itemprop="url" href="'''+url+'''"></a>
 <meta itemprop="startDate" content="'''+start+'''"/>
 <meta itemprop="endDate" content="'''+end+'''"/>
 <div itemprop="location"><span itemprop="name">Centro Cultural Guaires</span></div>
 </div><span class="evcal_event_title">CONVERSACIONES CON MI MENTE - JOAQUÍN CASERZA</span>
 <span class="evcal_event_subtitle">Festival de humor</span></div>'''

class GaldarTest(unittest.TestCase):
 def test_datetime_exact(self):
  self.assertEqual(g.parse_schema_date("2026-11-7T20:00+1:00"),dt.datetime(2026,11,7,20))
  self.assertIsNone(g.parse_schema_date("nonsense"))
 def test_extract_factual_fields(self):
  out=g.extract(BeautifulSoup(row(),"html.parser"),dt.date(2026,10,25),s.PLACES,s.norm,s.category)
  self.assertEqual(len(out),1)
  e=out[0]
  self.assertEqual(e["start"],"2026-11-07T20:00:00")
  self.assertEqual(e["end"],"2026-11-07T22:00:00")
  self.assertEqual(e["venue"],"Centro Cultural Guaires")
  self.assertEqual(e["price"],"")
  self.assertIsNone(e["free"])
  self.assertIn("galdar.es/events/",e["source_url"])
 def test_does_not_import_stale_or_other_host(self):
  with self.assertRaises(ValueError):
   g.extract(BeautifulSoup(row(start="2026-09-07T20:00+1:00",end="2026-09-07T22:00+1:00"),"html.parser"),
     dt.date(2026,10,25),s.PLACES,s.norm,s.category)
  with self.assertRaises(ValueError):
   g.extract(BeautifulSoup(row(url="https://evil.example/events/a/"),"html.parser"),
     dt.date(2026,10,25),s.PLACES,s.norm,s.category)
 def test_calendar_multiday_without_fake_daily_sessions(self):
  out=g.extract(BeautifulSoup(row(start="2026-11-07T20:00+1:00",end="2026-11-10T23:00+1:00"),"html.parser"),
     dt.date(2026,10,25),s.PLACES,s.norm,s.category)
  self.assertEqual(out[0]["start"],"2026-11-07")
  self.assertEqual(out[0]["end"],"2026-11-10")

if __name__=="__main__":unittest.main()
