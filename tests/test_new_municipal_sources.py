import datetime as dt,json,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import santabrigida_agenda as sb,teror_auditorio as te,telde_fiestas as tl
import sync_events as sync
DATE=dt.date(2026,10,25)

class MunicipalIntegrationsTest(unittest.TestCase):
 def test_santa_brigida_period_no_fake_sessions(self):
  obj=[{"@type":"Event","eventStatus":"https://schema.org/EventScheduled",
       "name":"Fiestas y talleres de noviembre",
       "url":"https://eventos.santabrigida.es/eventos/talleres-noviembre/",
       "startDate":"2026-10-25T05:00:00+00:00","endDate":"2026-11-20T18:00:00+00:00",
       "location":{"name":"Centro Cultural"}}]
  soup=BeautifulSoup('<script type="application/ld+json">'+json.dumps(obj)+'</script>',"html.parser")
  e=sb.extract_pages([soup,soup],DATE,sync.PLACES,sync.category)
  self.assertEqual(len(e),1)
  self.assertEqual((e[0]["start"],e[0]["end"]),("2026-10-25","2026-11-20"))
  self.assertIsNone(e[0]["free"])
  self.assertEqual(e[0]["price"],"")
 def test_santa_brigida_suspect_time_suppressed(self):
  o={"@type":"Event","name":"Pasacalle infantil", "url":"https://eventos.santabrigida.es/eventos/pasacalle/",
     "startDate":"2026-10-30T05:00:00+00:00","endDate":"2026-10-30T18:30:00+00:00"}
  soup=BeautifulSoup('<script type="application/ld+json">'+json.dumps([o])+'</script>',"html.parser")
  e=sb.extract_pages([soup],DATE,sync.PLACES,sync.category)[0]
  self.assertEqual(e["start"],"2026-10-30")
 def test_santa_brigida_outside_domain_rejected(self):
  o={"@type":"Event","name":"Unverified third party","url":"https://example.org/eventos/fake/",
     "startDate":"2026-10-30T20:30:00+00:00"}
  soup=BeautifulSoup('<script type="application/ld+json">'+json.dumps([o])+'</script>',"html.parser")
  with self.assertRaises(ValueError):sb.extract_pages([soup],DATE,sync.PLACES,sync.category)
 def test_santa_brigida_months_cross_year(self):
  self.assertEqual(sb.month_urls(dt.date(2026,12,8)),[
     "https://eventos.santabrigida.es/eventos/mes/2026-12/",
     "https://eventos.santabrigida.es/eventos/mes/2027-01/"])
 def test_teror_source_price_and_periods(self):
  # The parser must find individual numbered acts with their own dates/prices.
  body="\n".join(f"{i}.- Obra de teatro {i}\n6 de NOVIEMBRE de 2026\n20:30 horas\nPRECIO: 10 €\n" for i in range(1,12))
  body=body.replace("7.- Obra de teatro 7\n6 de NOVIEMBRE de 2026\n20:30 horas\nPRECIO: 10 €",
                    "7.- Festival de cine\nDEL 16 AL 20 DE NOVIEMBRE DE 2026\nPRECIO: 5 € (Fianza)")
  soup=BeautifulSoup("<article><div class='entry-content'><p>PROGRAMA:</p><p>"+body.replace("\n","<br/>")+"</p></div></article>","html.parser")
  items=te.extract(soup,DATE,sync.PLACES,sync.category)
  self.assertGreaterEqual(len(items),9)
  festival=next(e for e in items if "Festival de cine" in e["title"])
  self.assertEqual((festival["start"],festival["end"]),("2026-11-16","2026-11-20"))
  self.assertEqual(festival["price"],"")
  rest=next(e for e in items if "Obra de teatro" in e["title"])
  self.assertEqual(rest["start"],"2026-11-06T20:30:00")
  self.assertEqual(rest["price"],"10 €")
 def test_teror_annual_calendar_does_not_make_future_dates(self):
  soup=BeautifulSoup("<article><div class='entry-content'>Programa recurrente: octubre y noviembre</div></article>","html.parser")
  with self.assertRaises(ValueError):te.extract(soup,DATE,sync.PLACES,sync.category)
 def test_telde_announcements_expire_and_are_not_free_by_default(self):
  pages={}
  for key in tl.NOTICES:
   combined=" ".join(token for row in tl.ITEMS if row[0]==key for token in row[5])
   pages[key]=BeautifulSoup("<article>Programación 2026 "+combined+"</article>","html.parser")
  events=tl.extract(pages,DATE,sync.PLACES,sync.category)
  self.assertEqual(len(events),7)
  self.assertEqual(len([e for e in events if "2026-10-31" in e["start"]]),4)
  self.assertTrue(all(e["price"]=="" and e["free"] is None for e in events))
  self.assertEqual(tl.extract(pages,dt.date(2026,11,18),sync.PLACES,sync.category),[])
 def test_telde_missing_verification_blocks_import(self):
  pages={k:BeautifulSoup("<article>Programación 2026</article>","html.parser") for k in tl.NOTICES}
  with self.assertRaises(ValueError):tl.extract(pages,DATE,sync.PLACES,sync.category)
 def test_municipal_inventory_statuses(self):
  obj=json.loads((ROOT/"data"/"municipal_sources_gc.json").read_text(encoding="utf8"))
  statuses={e["municipality"]:e["status"] for e in obj["municipalities"]}
  self.assertEqual(len(statuses),21)
  self.assertEqual(statuses["Santa Brígida"],"conector_activo")
  self.assertEqual(statuses["Teror"],"conector_parcial")
  self.assertEqual(statuses["Telde"],"conector_parcial")
if __name__=="__main__":unittest.main()
