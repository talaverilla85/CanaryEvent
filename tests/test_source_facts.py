import sqlite3,sys,unittest,datetime as dt
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import source_facts, cabildo_public, sync_events as app

def page(head,details):
 html=('<html><h1 class="event-detail__title">Concierto de prueba</h1>'+
       '<div class="event-detail__details-list">'+''.join('<p class="event-detail__text">'+x+'</p>' for x in details)+'</div>'+
       '<script type="application/ld+json">'+head+'</script></html>')
 return BeautifulSoup(html,'html.parser')

class OfficialFactsTest(unittest.TestCase):
 def test_price_and_venue_from_schema(self):
  soup=page('{"@type":"Event","offers":{"price":"12,50","priceCurrency":"EUR"},"location":{"@type":"Place","name":"Teatro Cuyás"}}',
    ["Las Palmas de Gran Canaria","25/10/2026"])
  x=source_facts.enhance(soup,"Las Palmas de Gran Canaria",app.norm,False)
  self.assertEqual(x["venue"],"Teatro Cuyás")
  self.assertEqual(x["price"],"12,50 €")
  self.assertEqual(x["free"],0)

 def test_free_only_explicit(self):
  soup=page('{"@type":"Event","isAccessibleForFree":true}',["Ingenio","25/10/2026"])
  x=source_facts.enhance(soup,"Ingenio",app.norm,False)
  self.assertEqual(x["price"],"Gratis")
  self.assertEqual(x["free"],1)

 def test_no_price_not_assumed_from_ticket_link(self):
  soup=page('{"@type":"Event","description":"Entrada a la actividad. Consulta los detalles"}',
      ["Teatro Guiniguada","Las Palmas de Gran Canaria","25/10/2026"])
  x=source_facts.enhance(soup,"Las Palmas de Gran Canaria",app.norm,False)
  self.assertEqual(x["venue"],"Teatro Guiniguada")
  self.assertEqual(x["price"],"")
  self.assertIsNone(x["free"])

 def test_multiday_program_avoids_false_ticket_price(self):
  soup=page('{"@type":"Event","description":"Precio único: 10 € por una de las sesiones"}',
    ["Ingenio","24/10/2026 - 10/11/2026"])
  x=source_facts.enhance(soup,"Ingenio",app.norm,True)
  self.assertEqual(x["price"],"")

 def test_original_reference_link_not_claimed_price(self):
  soup=BeautifulSoup('''<div class="event-detail__details-list">
    <a href="https://www.instagram.com/p/123/">Red social</a>
    <a href="https://entradas.elteatroguiniguada.com/teatro/123">Entradas</a></div>''','html.parser')
  self.assertEqual(source_facts.organizer_link(soup),"https://entradas.elteatroguiniguada.com/teatro/123")
  self.assertEqual(source_facts.valid_outbound("javascript:alert(1)"),"")
  self.assertEqual(source_facts.valid_outbound("https://127.0.0.1/x"),"")

 def test_catalog_exports_external_link(self):
  with sqlite3.connect(":memory:") as conn:
   conn.row_factory=sqlite3.Row
   app.init(conn)
   self.assertIn("organizer_url",[x[1] for x in conn.execute("PRAGMA table_info(events)")])
   e={"title":"Concierto", "start":app.TODAY.isoformat()+"T20:00:00",
     "end":None,"municipality":"Ingenio","venue":"Teatro Municipal",
     "category":"musica","free":None,"price":"","details":"",
     "source_name":"Cabildo","source_url":"https://www.eventosgrancanaria.com/event/E-20261024-0001/concierto",
     "organizer_url":"https://cabildo.grancanaria.com/agenda","status":"approved"}
   self.assertEqual(app.upsert(conn,e),"added")
   self.assertEqual(conn.execute("SELECT organizer_url FROM events").fetchone()[0],e["organizer_url"])

if __name__=="__main__":unittest.main()
