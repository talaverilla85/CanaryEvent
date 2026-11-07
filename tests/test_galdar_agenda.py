import datetime as dt,sys,unittest
from unittest.mock import Mock,patch
import requests
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
 def test_transient_timeout_retries_once_without_bypassing_robots(self):
  response=Mock()
  client=Mock()
  client.get.side_effect=[requests.exceptions.ReadTimeout("slow"),response]
  with patch.object(g.time,"sleep") as delay:
   self.assertIs(g._request(client,g.URL,timeout=22),response)
  self.assertEqual(client.get.call_count,2)
  delay.assert_called_once_with(1)

 def test_repeated_timeout_still_reports_real_failure(self):
  client=Mock()
  client.get.side_effect=requests.exceptions.ReadTimeout("still slow")
  with patch.object(g.time,"sleep"):
   with self.assertRaises(requests.exceptions.ReadTimeout):
    g._request(client,g.URL,timeout=22)
  self.assertEqual(client.get.call_count,2)

 def test_no_retry_on_http_restriction(self):
  response=Mock()
  response.status_code=403
  client=Mock()
  client.get.return_value=response
  with patch.object(g.time,"sleep") as delay:
   self.assertIs(g._request(client,g.URL,timeout=22),response)
  self.assertEqual(client.get.call_count,1)
  delay.assert_not_called()

 def test_guaires_public_fetch_retry_after_robots_validation(self):
  response=Mock()
  response.content=b'<div class="eventon_list_event"></div>'
  response.raise_for_status.return_value=None
  with patch.object(s,"allowed") as allowed,patch.object(s.requests,"get",
        side_effect=[requests.exceptions.ReadTimeout("first"),response]) as get,patch.object(s.time,"sleep"):
   html=s.get_html("https://www.galdar.es/event-location/centro-cultural-guaires/")
  self.assertEqual(len(html.select(".eventon_list_event")),1)
  allowed.assert_called_once()
  self.assertEqual(get.call_count,2)

 def test_guaires_retry_is_host_scoped(self):
  with patch.object(s,"allowed"),patch.object(s.requests,"get",
       side_effect=requests.exceptions.ReadTimeout("one timeout")) as get,patch.object(s.time,"sleep"):
   with self.assertRaises(requests.exceptions.ReadTimeout):
    s.get_html("https://aguimes.es/event-location/teatro-auditorio-aguimes/")
  self.assertEqual(get.call_count,1)

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
