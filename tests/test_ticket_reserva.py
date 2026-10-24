import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import ticket_reserva as tr
import sync_events as app

def ticket(*,title="GRAN FINAL YO CANTO",town="Ingenio",from_="2026-10-24 20:30:00",
           to="2026-10-24 20:30:00",price="0.00",slug="gran-final-yo-canto",venue="Centro Cultural Federico García Lorca"):
 return {"id":1614,"slug":slug,"title":{"es":title},"date":from_,"from":from_,"to":to,
    "town":town,"location":{"es":venue},"lowest_fare":price,"is_free":False,"is_cancelled":False,
    "cover_image":"https://www.tureservaonline.es/storage/5355/Cartel-24.jpg","is_sold_out":False}

class TicketPlatformTests(unittest.TestCase):
 def test_tenerife_is_excluded(self):
  e=ticket(town="Santa Cruz De Tenerife")
  self.assertIsNone(tr.extract(e,dt.date(2026,10,24),app.PLACES,app.norm,app.category))
 def test_bounded_gc_municipalities(self):
  e=ticket(town="Teatro Víctor Jara (Vecindario)")
  x=tr.extract(e,dt.date(2026,10,24),app.PLACES,app.norm,app.category)
  self.assertEqual(x["municipality"],"Santa Lucía de Tirajana")
 def test_yo_canto_price_venue_and_time(self):
  x=tr.extract(ticket(),dt.date(2026,10,24),app.PLACES,app.norm,app.category)
  self.assertEqual(x["start"],"2026-10-24T20:30:00")
  self.assertEqual(x["venue"],"Centro Cultural Federico García Lorca")
  self.assertEqual(x["price"],"Desde 0 €")
  self.assertIn("gran-final-yo-canto",x["source_url"])
 def test_no_fake_daily_sessions(self):
  x=tr.extract(ticket(from_="2026-10-30 18:15:00",to="2026-11-01 22:45:00"),
    dt.date(2026,10,24),app.PLACES,app.norm,app.category)
  self.assertEqual(x["start"],"2026-10-30")
  self.assertEqual(x["end"],"2026-11-01")
  self.assertIn("varias fechas",x["details"])
 def test_prices_minimum_and_unknown(self):
  x=tr.extract(ticket(price="12.50"),dt.date(2026,10,24),app.PLACES,app.norm,app.category)
  self.assertEqual(x["price"],"Desde 12,50 €")
  y=tr.extract(ticket(price=None),dt.date(2026,10,24),app.PLACES,app.norm,app.category)
  self.assertEqual(y["price"],"")
  self.assertIsNone(y["free"])
 def test_images_remain_on_ticket_domain(self):
  a=ticket();a["cover_image"]="https://example.com/fake.jpg"
  self.assertEqual(tr.extract(a,dt.date(2026,10,24),app.PLACES,app.norm,app.category)["image_url"],"")
 def test_enrich_not_duplicate_existing_original(self):
  with sqlite3.connect(":memory:") as conn:
   conn.row_factory=sqlite3.Row
   app.init(conn)
   e={"title":"GRAN FINAL YO CANTO","start":"2026-10-24","end":None,
     "municipality":"Ingenio","venue":"Consultar el recinto en la ficha oficial",
     "category":"musica","free":None,"price":"","details":"Comprobar fuente",
     "source_name":"Portal del Cabildo",
     "source_url":"https://www.eventosgrancanaria.com/event/E-20261024-0001/gran-final-yo-canto",
     "status":"approved"}
   app.upsert(conn,e)
   t=tr.extract(ticket(),dt.date(2026,10,24),app.PLACES,app.norm,app.category)
   self.assertEqual(tr.reconcile(conn,t,app.norm,app.NOW),(1,1))
   self.assertEqual(tr.reconcile(conn,t,app.norm,app.NOW),(1,0))
   self.assertEqual(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],1)
   row=conn.execute("SELECT venue,price,organizer_url,start FROM events").fetchone()
   self.assertEqual(row["venue"],"Centro Cultural Federico García Lorca")
   self.assertEqual(row["price"],"Desde 0 €")
   self.assertTrue(row["organizer_url"].startswith("https://www.tureservaonline.es/"))
   self.assertEqual(row["start"],"2026-10-24T20:30:00")
 def test_cancelled_excluded(self):
  e=ticket();e["is_cancelled"]=True
  self.assertIsNone(tr.extract(e,dt.date(2026,10,24),app.PLACES,app.norm,app.category))

if __name__=="__main__":unittest.main()
