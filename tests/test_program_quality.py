import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import program_quality as q
import ingenio_juvenil_program as ing
import sync_events as sync

def program_page(image_id=ing.OFFICIAL_IMAGE_ID,title="Programación Otoño 2026 - Juventud de Ingenio",dates="24/09/2026 - 17/11/2026"):
 return ('<h1 class="event-detail__title">'+title+'</h1>'
  '<div class="event-detail__details-list"><p class="event-detail__text">'+dates+'</p></div>'
  '<img src="https://www.eventosgrancanaria.com/controlpanel/files/gridfs/'+image_id+'">')

def plan(title,start="2026-09-24",end="2026-11-17",venue="Consultar el recinto en la ficha oficial"):
 return dict(id=306,title=title,start=start,end=end,municipality="Ingenio",venue=venue,source_name="Cabildo",source_url=ing.PROGRAM_URL)

class ProgrammeQualityTests(unittest.TestCase):
 def test_ingenio_grouped_flyer_is_never_a_plan(self):
  e=plan("Programación Otoño 2026 - Juventud de Ingenio")
  self.assertTrue(q.is_multi_activity(e))
  accepted,review=q.filter_public_plans([e])
  self.assertEqual(accepted,[])
  self.assertEqual(len(review),1)
  self.assertEqual(review[0]["id"],306)

 def test_other_promotional_programmes_are_hidden(self):
  for title in (
    "Programación Día de las Bibliotecas 2026",
    "Programación La Grada Creativa Octubre 2026",
    "Programación Cultural - Centro Cultural Maspalomas",
    "Cursos y talleres de noviembre de la Universidad Popular",
    "Fiestas de San Rafael 2026 · Vecindario",
    "El Ayuntamiento de Agaete pone en marcha el programa de talleres Cuida de tu Bienestar"
  ):
   with self.subTest(title=title):
    self.assertTrue(q.is_multi_activity(plan(title)),title)

 def test_specific_single_exhibition_remains(self):
  self.assertFalse(q.is_multi_activity(plan("Exposición África: la fuerza escondida",end="2026-10-30")))
  self.assertFalse(q.is_multi_activity(plan("Pregón de las fiestas de San Gregorio",start="2026-11-06",end=None,venue="Plaza de San Gregorio")))
  self.assertFalse(q.is_multi_activity(plan("Concierto de Navidad",start="2026-12-20",end=None,venue="Auditorio")))

 def test_ingenio_actual_municipality_is_las_palmas(self):
  items=ing.extract(program_page(),dt.date(2026,10,26),sync.PLACES)
  self.assertEqual(len(items),1)
  x=items[0]
  self.assertEqual(x["start"],"2026-11-17T19:00:00")
  self.assertEqual(x["end"],"2026-11-17T20:30:00")
  self.assertEqual(x["municipality"],"Las Palmas de Gran Canaria")
  self.assertIn("Barranco de la Ballena",x["venue"])
  self.assertEqual(x["source_url"],ing.PROGRAM_URL)
  self.assertIsNone(x["free"])
  self.assertEqual(x["price"],"")
  self.assertNotIn("Hockey",x["title"])
  self.assertEqual(len(ing.UNRESOLVED),1)

 def test_official_poster_replacement_requires_review(self):
  for html in (program_page(image_id="FAKE"),program_page(title="Nueva programación sin verificar"),
               program_page(dates="25/09/2026 - 17/11/2026")):
   with self.assertRaises(ValueError):ing.extract(html,dt.date(2026,10,26),sync.PLACES)

 def test_programme_expires_and_loses_future_past_events(self):
  self.assertEqual(ing.extract(program_page(),dt.date(2026,11,18),sync.PLACES),[])

 def test_child_has_different_stable_key_from_official_poster(self):
  parent=plan("Programación Otoño 2026 - Juventud de Ingenio")
  child=ing.extract(program_page(),dt.date(2026,10,26),sync.PLACES)[0]
  self.assertNotEqual(sync.dedup_key(parent),sync.dedup_key(child))
  self.assertEqual(sync.dedup_key(child),sync.dedup_key(dict(child)))
 def test_no_fake_location_assignment(self):
  item=ing.extract(program_page(),dt.date(2026,10,26),sync.PLACES)[0]
  self.assertNotEqual(item["municipality"],"Ingenio")
  self.assertTrue(all("municipality" in p for p in ing.UNRESOLVED))

if __name__=="__main__":unittest.main()
