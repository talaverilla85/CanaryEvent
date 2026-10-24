import datetime as dt,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
import sync_events as a
import santalucia_festivals as f

MOCK_MAIN="""
<article>
<h1>Fiestas de San Rafael 2026</h1>
<p>El 16 de octubre comienzan las fiestas hasta el 1 de noviembre.</p>
<p>El domingo 25 concierto de Braulio a las 20 horas en el Recinto Ferial.</p>
<p>El lunes 26 actividades infantiles.</p>
<p>El jueves 29 noche de tapas.</p>
<p>El viernes 30 a las 20 horas Vecindario está de Tendere.</p>
<p>A las 22 horas concierto de Los Coquillos.</p>
<p>El domingo 1 de noviembre actuará Shaila Dúrcal.</p>
</article>
"""
MOCK_BRAULIO="<h1>Concierto gratuito de Braulio en San Rafael, domingo 25 de octubre</h1>"

class SantaLuciaFestivitiesTest(unittest.TestCase):
 def test_published_times_and_free_are_explicit(self):
  items=f.extract(MOCK_MAIN,MOCK_BRAULIO,dt.date(2026,10,25),a.norm,a.category,a.PLACES)
  self.assertEqual(len(items),7)
  braulio=next(x for x in items if "Braulio" in x["title"])
  self.assertEqual(braulio["start"],"2026-10-25T20:00:00")
  self.assertEqual((braulio["price"],braulio["free"]),("Gratis",1))
  tapas=next(x for x in items if "Tapas" in x["title"])
  self.assertEqual(tapas["start"],"2026-10-29")
  self.assertEqual(tapas["price"],"")
  self.assertTrue(tapas["venue"].startswith("Consultar"))
 def test_stops_after_end_of_festival(self):
  self.assertEqual(f.extract(MOCK_MAIN,MOCK_BRAULIO,dt.date(2026,11,2),a.norm,a.category,a.PLACES),[])
 def test_does_not_invent_gratuity(self):
  with self.assertRaises(ValueError):
   f.extract(MOCK_MAIN,"Concierto de Braulio",dt.date(2026,10,25),a.norm,a.category,a.PLACES)
 def test_missing_municipal_notice_is_not_accepted(self):
  with self.assertRaises(ValueError):
   f.extract("<p>San Rafael 2026</p>",MOCK_BRAULIO,dt.date(2026,10,25),a.norm,a.category,a.PLACES)
 def test_current_day_entries_only(self):
  items=f.extract(MOCK_MAIN,MOCK_BRAULIO,dt.date(2026,10,30),a.norm,a.category,a.PLACES)
  self.assertTrue(all((e["end"] or e["start"])[:10]>="2026-10-30" for e in items))

if __name__=="__main__":unittest.main()
