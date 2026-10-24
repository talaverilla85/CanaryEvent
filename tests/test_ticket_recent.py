import datetime as dt
import json
import sqlite3
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_events as app
import ticket_recent as ticket

class FakeResponse:
 def __init__(self,body,content_type="application/json"):
  self.status_code=200
  self.content=(body.encode("utf-8") if isinstance(body,str) else body)
  self.text=self.content.decode("utf-8")
 def raise_for_status(self):return None
 def json(self):return json.loads(self.text)

class FakeClient:
 def get(self,url,**kwargs):
  if url.endswith("/robots.txt"):return FakeResponse("User-agent: *\nAllow: /\n")
  if url.endswith("/sitemap.xml"):
   return FakeResponse("""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://www.tureservaonline.es/es/events/gran-final-yo-canto</loc></url></urlset>""")
  if url.endswith("/api/events/gran-final-yo-canto"):
   return FakeResponse(json.dumps({"lang_title":"GRAN FINAL YO CANTO",
     "town":{"name":"Ingenio"},"location":{"lang_name":"Centro Cultural Federico García Lorca"},
     "date":"24-10-2026 20:30","fares":[{"published":1,"price":"0.00"}],
     "coverimage":{"original":[{"url":"https://www.tureservaonline.es/storage/5355/Cartel-24.jpg"}]},
     "is_cancelled":0,
     "user":{"provider":{"payment_token":"Never retain user/provider data"}}}))
  raise RuntimeError("Unexpected URL "+url)

class RecentTicketTests(unittest.TestCase):
 def test_zero_all_published_fares_is_free(self):
  self.assertEqual(ticket.price_from_public_fares({
    "fares":[{"published":1,"price":"0.00"},{"published":1,"price":"0.00"}]}),("Gratis",1))
  self.assertEqual(ticket.price_from_public_fares({
    "fares":[{"published":1,"price":"0.00"},{"published":1,"price":"7.50"}]}),("Desde 0 €",0))
 def test_source_first_duplicate_and_no_payment_fields_persisted(self):
  with sqlite3.connect(":memory:") as conn:
   conn.row_factory=sqlite3.Row
   app.init(conn)
   direct={"title":"GRAN FINAL YO CANTO","start":"2026-10-24T20:30:00","end":None,
     "municipality":"Ingenio","venue":"Centro Cultural Federico García Lorca","category":"musica",
     "price":"","free":None,"details":"","source_name":"Ayuntamiento de Ingenio",
     "source_url":"https://ingenio.es/events/gran-final-yo-canto/","status":"approved"}
   cab=dict(direct)
   cab.update(municipality="Las Palmas de Gran Canaria",venue="Consultar el recinto en la ficha oficial",
     source_name="Portal oficial de Eventos Gran Canaria (Cabildo)",
     source_url="https://www.eventosgrancanaria.com/event/E-20261024-0019/gran-final-yo-canto",
     organizer_url="https://ingenio.es/events/gran-final-yo-canto/",start="2026-10-24")
   app.upsert(conn,direct)
   app.upsert(conn,cab)
   result=ticket.reconcile_recent(conn,app.NOW,dt.date(2026,10,24),app.PLACES,app.norm,
                   client=FakeClient(),max_details=2)
   self.assertEqual(result["examined"],1)
   self.assertEqual(result["enriched"],2)
   rows=conn.execute("SELECT * FROM events ORDER BY id").fetchall()
   official=next(x for x in rows if x["municipality"]=="Ingenio")
   double=next(x for x in rows if x["municipality"]=="Las Palmas de Gran Canaria")
   self.assertEqual(official["price"],"Gratis")
   self.assertEqual(official["organizer_url"],"https://www.tureservaonline.es/es/events/gran-final-yo-canto")
   self.assertEqual(double["status"],"duplicate")
   self.assertEqual(official["source_url"],direct["source_url"])
   self.assertNotIn("payment_token",dict(official))
   app.upsert(conn,cab)
   self.assertEqual(conn.execute("SELECT status FROM events WHERE id=?",(double["id"],)).fetchone()[0],"duplicate")

if __name__=="__main__":unittest.main()
