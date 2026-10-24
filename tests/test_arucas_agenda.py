import datetime as dt,json,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import arucas_agenda as ar
import sync_events as sync

def html_card(title,date,href="modules.php?mod=portal&file=ver_gen&id=QTExUT09"):
 return '<article><div class="entry-media"><a class="image-post" href="'+href+'">foto</a></div><span class="entry-title">'+title+'</span><span class="posted-on"><strong>'+date+'</strong></span></article>'

class ArucasMunicipalityTests(unittest.TestCase):
 def test_all_official_21_municipalities(self):
  o=json.loads((ROOT/"data/municipal_sources_gc.json").read_text(encoding="utf8"))
  self.assertEqual(len(o["municipalities"]),21)
  self.assertEqual(len({r["municipality"] for r in o["municipalities"]}),21)
  self.assertEqual(set(sync.PLACES),{r["municipality"] for r in o["municipalities"]})
  self.assertTrue(all(r["official_website"].startswith("https://") for r in o["municipalities"]))
 def test_date_range_without_inventing_hour(self):
  self.assertEqual(ar.date_window("Del 23 de octubre al 21 de noviembre",2026),(dt.date(2026,10,23),dt.date(2026,11,21)))
  self.assertEqual(ar.date_window("14 y 15 de noviembre",2026),(dt.date(2026,11,14),dt.date(2026,11,15)))
  self.assertEqual(ar.date_window("Sábado 31 de octubre",2026),(dt.date(2026,10,31),dt.date(2026,10,31)))
  self.assertIsNone(ar.date_window("De septiembre a diciembre",2026))
 def test_extract_no_unverified_price_venue(self):
  soup=BeautifulSoup(html_card("DIVINA MUERTE 2026","Del 23 de octubre al 21 de noviembre"),"html.parser")
  out=ar.extract(soup,dt.date(2026,10,25),sync.PLACES,sync.norm,sync.category)
  self.assertEqual(len(out),1)
  self.assertEqual(out[0]["municipality"],"Arucas")
  self.assertEqual(out[0]["start"],"2026-10-23")
  self.assertEqual(out[0]["end"],"2026-11-21")
  self.assertEqual(out[0]["price"],"")
  self.assertIsNone(out[0]["free"])
  self.assertEqual(out[0]["venue"],"Consultar el recinto en la ficha oficial")
  self.assertIn("file=ver_gen",out[0]["source_url"])
 def test_invalid_external_or_stale(self):
  evil=html_card("Verano","Sábado 31 de octubre","https://example.org/redirect")
  past=html_card("Fiesta antigua","17 de septiembre")
  with self.assertRaises(ValueError):
   ar.extract(BeautifulSoup(evil+past,"html.parser"),dt.date(2026,10,25),sync.PLACES,sync.norm,sync.category)
 def test_missing_robots_permission_fails_closed(self):
  class Resp:
   def __init__(self,code):self.status_code=code;self.text=""
  class Fake:
   def get(self,*args,**kwargs):return Resp(403)
  with self.assertRaises(RuntimeError):ar.fetch_listing(Fake())
 def test_recurring_names_do_not_generate_years_without_end(self):
  self.assertIsNone(ar.date_window("De octubre 2026 a febrero 2027",2026))

if __name__=="__main__":unittest.main()
