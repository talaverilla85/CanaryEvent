import datetime as dt,sys,unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import source_facts,venue_facts,cabildo_public,sync_events

class DescriptionVenueRecognition(unittest.TestCase):
 def test_official_venue_as_subject(self):
  desc="El próximo miércoles 28 de octubre a las 12:30 horas, el vestíbulo de la Facultad de Veterinaria será el escenario de una breve actuación musical."
  self.assertEqual(venue_facts.from_description(desc,"Arucas"),"vestíbulo de la Facultad de Veterinaria")
  doc=BeautifulSoup('<script type="application/ld+json">{"@type":"Event","name":"Musicampus","location":{"@type":"Place","name":"Arucas"},"description":"'+desc+'"}</script>',"html.parser")
  self.assertEqual(source_facts.verified_venue(doc,source_facts.event_schema(doc),"Arucas",sync_events.norm),"vestíbulo de la Facultad de Veterinaria")
 def test_unsupported_subject_mention_not_a_venue(self):
  samples=[
   "La Facultad de Veterinaria organiza una charla, pero el recinto aún no se confirma.",
   "Consulta a la Facultad de Veterinaria para más información sobre la inscripción.",
   "El acto se desarrolla en varias sedes. El vestíbulo de la Facultad de Veterinaria será el escenario de una actividad.",
   "Presentación de la poeta. Más información: Casa-Museo Tomás Morales, plaza Tomás Morales.",
  ]
  for item in samples:
   with self.subTest(text=item):
    self.assertEqual(venue_facts.from_description(item,"Arucas"),"")
 def test_single_named_venue_not_eclipsed_by_organizer(self):
  self.assertEqual(venue_facts.from_description(
      "La ULPGC y la Facultad de Veterinaria organizan el acto. En el vestíbulo de la Facultad de Veterinaria habrá una interpretación.",
      "Arucas"),"vestíbulo de la Facultad de Veterinaria")

if __name__=="__main__":unittest.main()
