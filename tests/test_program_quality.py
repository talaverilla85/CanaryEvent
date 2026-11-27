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

 def test_facility_booking_is_not_published_as_event(self):
  booking=plan("RESERVA ÁREA RECREATIVA HUERTAS DEL REY",start="2026-06-06",end="2027-01-03",venue="Área Recreativa Huertas del Rey")
  self.assertTrue(q.is_non_event_listing(booking))
  events,review=q.filter_public_plans([booking])
  self.assertEqual(events,[])
  self.assertIn("Reserva administrativa",review[0]["reason"])

 def test_booking_rule_preserves_actual_events_and_registration(self):
  for title in ("Concierto de Navidad · Reserva tus entradas",
                "Reserva de entradas para teatro infantil",
                "Área recreativa: Taller de senderismo",
                "Ruta guiada por Huertas del Rey"):
   with self.subTest(title=title):
    self.assertFalse(q.is_non_event_listing(plan(title)),title)

 def test_specific_single_exhibition_remains(self):
  self.assertFalse(q.is_multi_activity(plan("Exposición África: la fuerza escondida",end="2026-10-30")))
  self.assertFalse(q.is_multi_activity(plan("Pregón de las fiestas de San Gregorio",start="2026-11-06",end=None,venue="Plaza de San Gregorio")))
  self.assertFalse(q.is_multi_activity(plan("Concierto de Navidad",start="2026-12-20",end=None,venue="Auditorio")))


 def test_closed_registration_excursion_does_not_return_as_public_event(self):
  excursion=plan("«SALIDA CULTURAL JARDÍN DE LA MARQUESA»",
                start="2026-11-27T09:00:00",end="2026-11-27T18:00:00",
                venue="Club Municipal de Mayores de Santa Brígida")
  excursion.update(id=941,municipality="Santa Brígida",
   source_url="https://eventos.santabrigida.es/eventos/salida-cultural-jardin-de-la-marquesa/",
   details=("Actividad dirigida a socios del Club de Mayores; el público general "
            "solo puede participar si quedan plazas libres. Inscripción presencial "
            "anunciada del 16 al 18 de noviembre (8:00–14:00)."))
  self.assertIn("Acceso al público general condicionado",
                q.public_access_blocker(excursion,dt.date(2026,11,27)))
  accepted,held=q.filter_public_plans([excursion],dt.date(2026,11,27))
  self.assertFalse(accepted)
  self.assertEqual(held[0]["id"],941)
  self.assertIn("plazas",held[0]["reason"])

 def test_conditional_membership_in_other_source_is_also_held(self):
  item=plan("Taller de coronas de Adviento",start="2026-12-01T09:30:00",
             end=None,venue="Club de Mayores de Santa Brígida")
  item["details"]=("Inscripción presencial a partir del 24 de noviembre. "
                    "Dirigido a soci@s del Club de mayores (si quedan plazas "
                    "se cubrirán con público en general).")
  self.assertIn("Acceso al público general condicionado",
                q.public_access_blocker(item,dt.date(2026,11,27)))
  accepted,held=q.filter_public_plans([item],dt.date(2026,11,27))
  self.assertEqual(accepted,[])
  self.assertEqual(len(held),1)

 def test_expired_explicit_deadline_disqualifies_regardless_of_event_date(self):
  item=plan("Excursión cultural",start="2026-12-02T10:00:00",
            end=None,venue="Parque de Arucas")
  item["details"]="Inscripción hasta el 20 de noviembre de 2026. Abierta al público."
  self.assertIn("Inscripción cerrada",q.public_access_blocker(item,dt.date(2026,11,27)))
  self.assertEqual(q.public_access_blocker(item,dt.date(2026,11,19)),"")
  item["details"]="Inscripción del 16 al 18 de noviembre de 2026."
  self.assertIn("Inscripción cerrada",q.public_access_blocker(item,dt.date(2026,11,27)))

 def test_no_overbroad_exclusion_of_ticketed_age_limited_or_open_events(self):
  for details in (
   "Exclusivo para jóvenes de 12 a 30 años. Consulta plazas e inscripción.",
   "Reserva de entradas para una sesión familiar de teatro.",
   "Taller del Club de Mayores con participación abierta al público.",
   "Inscripción a partir del 24 de noviembre, mientras queden plazas.",
   "Inscripción hasta el 10 de diciembre de 2026.",
   "Entrada de pago: 16 € y reserva obligatoria, plazas limitadas."
  ):
   with self.subTest(details=details):
    item=plan("Taller creativo para adultos",start="2026-12-10T18:00:00",
              end=None,venue="Centro Cultural")
    item["details"]=details
    self.assertFalse(q.public_access_blocker(item,dt.date(2026,11,27)))
    accepted,held=q.filter_public_plans([item],dt.date(2026,11,27))
    self.assertEqual(len(accepted),1)
    self.assertEqual(held,[])

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
