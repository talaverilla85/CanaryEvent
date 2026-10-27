import datetime as dt,json,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import tejeda_agenda as tej
import sync_events as sync
DATE=dt.date(2026,10,27)
def page(body,published="2026-10-21"):
 return BeautifulSoup('<html><head><meta property="article:published_time" content="'+published+'T10:00:00+00:00"></head><body><div class="entry-content">'+body+'</div></body></html>',"html.parser")

class TejedaOfficialAgendaTest(unittest.TestCase):
 def test_one_verified_future_schedule(self):
  body="El sábado 31 de octubre, a partir de las 20:00 horas, en el Club de Pensionistas y Simpatizantes Texeda."
  r=tej.parse_article(page(body),"Noche de Baile – Noche de los Finaos 2026",
      "https://tejeda.eu/noche-de-baile-noche-de-los-finaos-2026/",DATE,sync.category)
  self.assertEqual(r["start"],"2026-10-31T20:00:00")
  self.assertEqual(r["municipality"],"Tejeda")
  self.assertIsNone(r["free"])
  self.assertEqual(r["venue"],"Club de Pensionistas y Simpatizantes Texeda")
 def test_date_only_when_no_clock_verified(self):
  r=tej.parse_article(page("El próximo domingo 1 de noviembre en la Plaza de Ntra. Sra. del Socorro."),
   "Tejeda en Copa 2026","https://tejeda.eu/tejeda-en-copa-2026/",DATE,sync.category)
  self.assertEqual(r["start"],"2026-11-01")
  self.assertEqual(r["price"],"")
 def test_does_not_infer_recurring_wednesdays_or_old_article(self):
  self.assertIsNone(tej.parse_article(page("Sesiones todos los miércoles de noviembre y diciembre de 2026"),"Taller",
    "https://tejeda.eu/taller/",DATE,sync.category))
  self.assertIsNone(tej.parse_article(page("El 31 de octubre a las 20:00 horas.","2025-10-21"),"Noche",
    "https://tejeda.eu/noche/",DATE,sync.category))
 def test_invalid_weekday_rejected(self):
  self.assertIsNone(tej.parse_article(page("El martes 31 de octubre a las 20:00 horas."),"Fiesta",
    "https://tejeda.eu/fiesta/",DATE,sync.category))
 def test_explicit_free_only_and_no_guess(self):
  r=tej.parse_article(page("El lunes 2 de noviembre de 2026 nos vamos de ruta. Salida desde la gasolinera DISA Tejeda a las 09:30 horas. Actividad Gratuita."),"Ruta en Buggy",
   "https://tejeda.eu/ruta-en-buggy/",DATE,sync.category)
  self.assertEqual(r["start"],"2026-11-02T09:30:00")
  self.assertEqual((r["free"],r["price"]),(1,"Gratis"))
 def test_links_are_official(self):
  doc='<article><h4 class="brbl-post-title"><a href="https://tejeda.eu/tejeda-en-copa-2026/">Tejeda en Copa</a></h4></article>'
  out=tej.discover_cards(BeautifulSoup(doc,"html.parser"))
  self.assertEqual(len(out),1)
  with self.assertRaises(ValueError):
   tej.discover_cards(BeautifulSoup(doc.replace("https://tejeda.eu","https://example.com"),"html.parser"))
 def test_registry(self):
  j=json.loads((ROOT/"data"/"municipal_sources_gc.json").read_text(encoding="utf8"))
  status={x["municipality"]:x["status"] for x in j["municipalities"]}
  self.assertEqual(status["Tejeda"],"conector_activo")
  self.assertTrue(status["Firgas"].startswith("agenda_localizada"))
  self.assertTrue(status["Agaete"].startswith("agenda_localizada"))
if __name__=="__main__":unittest.main()
