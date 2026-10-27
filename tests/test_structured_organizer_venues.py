import sqlite3,sys,unittest,datetime as dt
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import structured_organizer_venues as o
import organizer_venues as org
class StructuredVenueTests(unittest.TestCase):
 def test_organizer_allowlist_and_private_domains_denied(self):
  self.assertEqual(org.valid_url("https://ofgrancanaria.com/conciertos-entradas/eventos/calling-all-dawns-ces2/440"),"https://ofgrancanaria.com/conciertos-entradas/eventos/calling-all-dawns-ces2/440")
  self.assertEqual(org.valid_url("https://www.casafrica.es/es/evento/nyeleni"),"https://www.casafrica.es/es/evento/nyeleni")
  self.assertEqual(org.valid_url("https://evil.casafrica.es/es/evento/nyeleni"),"")
  self.assertEqual(org.valid_url("https://ofgrancanaria.com.evil.test/a"),"")
 def test_ofgc_date_specific_room(self):
  s=BeautifulSoup('''<div class="event__information">
    <div class="event__show-container"><p>04/11/2026 - 10:00 <br>Sala Gabriel Rodó</p></div>
    <div class="event__show-container"><p>04/11/2026 - 11:30 <br>Sala Gabriel Rodó</p></div>
    <div class="event__show-container"><p>05/11/2026 - 10:00 <br>Teatro Pérez Galdós</p></div>
    </div>''',"html.parser")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-04"),"Sala Gabriel Rodó")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-05"),"Teatro Pérez Galdós")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-06"),"")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-04","15:00"),"")
 def test_reject_conflicting_room_on_same_day(self):
  s=BeautifulSoup('''<div class="event__information">
    <div class="event__show-container"><p>05/11/2026 - 10:00<br>Sala Gabriel Rodó</p></div>
    <div class="event__show-container"><p>05/11/2026 - 12:00<br>Sala Josefina de la Torre</p></div>
    </div>''',"html.parser")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-05"),"")
  self.assertEqual(o.extract(s,"https://ofgrancanaria.com/a","Las Palmas de Gran Canaria","2026-11-05","12:00"),"Sala Josefina de la Torre")
 def test_lpa_place_link_only(self):
  s=BeautifulSoup('''<div class="mt-12">
    <div class="event-show-title"><span>Lugar</span></div>
    <div><p><a href="https://lpacultura.com/places/espacio-cultural-jesus-arencibia">Espacio Cultural Jesús Arencibia</a></p></div></div>''',"html.parser")
  self.assertEqual(o.extract(s,"https://lpacultura.com/events/microzarzuelas","Las Palmas de Gran Canaria","2026-11-05"),"Espacio Cultural Jesús Arencibia")
  s.find("a")["href"]="https://example.net/places/espacio-cultural-jesus-arencibia"
  self.assertEqual(o.extract(s,"https://lpacultura.com/events/microzarzuelas","Las Palmas de Gran Canaria","2026-11-05"),"")
 def test_casa_africa_map_coords_not_confused(self):
  s=BeautifulSoup('''<div><div class="fw-bold">Lugar:</div><div class="fw-bold gray-dark">
    Casa de Colón<div class="geolocation-map"><p>28.101613, -15.41399</p></div>
    </div></div>''',"html.parser")
  self.assertEqual(o.extract(s,"https://www.casafrica.es/es/evento/nyeleni","Las Palmas de Gran Canaria","2026-11-06"),"Casa de Colón")
  s.select_one(".gray-dark").insert(0,"Museo otra sede")
  self.assertEqual(o.extract(s,"https://www.casafrica.es/es/evento/nyeleni","Las Palmas de Gran Canaria","2026-11-06"),"")
 def test_outside_municipality_does_not_pass_geo_gate(self):
  s=BeautifulSoup("""<div class="fw-bold">Lugar:</div>
   <div class="fw-bold gray-dark">Teatro Auditorio de Agüimes
   <div data-lat="27.90" data-lng="-15.44"></div></div>""","html.parser")
  self.assertFalse(o.municipality_consistent(s,"https://www.casafrica.es/es/evento/a",
    "Las Palmas de Gran Canaria","Teatro Auditorio de Agüimes"))
  self.assertFalse(o.municipality_consistent(s,"https://www.casafrica.es/es/evento/a",
    "Las Palmas de Gran Canaria","Museo Nacional Centro de Arte Reina Sofía"))
  self.assertFalse(o.municipality_consistent(s,"https://www.casafrica.es/es/evento/a",
    "Las Palmas de Gran Canaria","Universidad París 8, París"))
 def test_named_casa_colon_with_local_coords_accepted(self):
  s=BeautifulSoup("""<div data-lat="28.10161300848" data-lng="-15.41399715"></div>""","html.parser")
  self.assertTrue(o.municipality_consistent(s,"https://www.casafrica.es/es/evento/a",
    "Las Palmas de Gran Canaria","Casa de Colón"))
 def test_no_foreign_municipality_for_foreign_host(self):
  s=BeautifulSoup("<main></main>","html.parser")
  self.assertFalse(o.municipality_consistent(s,"https://ofgrancanaria.com/a",
    "Las Palmas de Gran Canaria","Teatro Auditorio de Agüimes"))
 def test_unknown_host_does_not_guess(self):
  s=BeautifulSoup("<p>Lugar Casa de Colón</p>","html.parser")
  self.assertEqual(o.extract(s,"https://unknown.example/events/nyeleni","Las Palmas de Gran Canaria","2026-11-06"),"")
if __name__=="__main__":unittest.main()
