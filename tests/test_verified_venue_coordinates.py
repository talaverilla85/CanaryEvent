import json,sqlite3,sys,unittest,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import verified_venue_coordinates as geo
import sync_events as app

class VerifiedVenueGeoTests(unittest.TestCase):
 def test_normalization_aliases(self):
  result=geo.find("Las Palmas de Gran Canaria","Teatro Pérez Galdós.")
  self.assertIsNotNone(result)
  self.assertAlmostEqual(result[0],28.1035634,5)
  self.assertEqual(geo.find("Las Palmas de Gran Canaria","Museo Elder"),geo.find("Las Palmas de Gran Canaria","Museo Elder de la Ciencia y la Tecnología"))
 def test_only_verified_municipality_and_venue(self):
  self.assertIsNone(geo.find("Telde","Teatro Pérez Galdós"))
  self.assertIsNone(geo.find("Las Palmas de Gran Canaria","Teatro Pérez Galdós y Sala Insular de Teatro"))
  self.assertIsNone(geo.find("Las Palmas de Gran Canaria","Consultar el recinto en la ficha oficial"))
  self.assertIsNone(geo.find("Arucas","Recinto por confirmar"))
 def test_fallback_centroid(self):
  lat,lng,a=geo.resolve("Telde","Biblioteca sin ubicación oficial",app.PLACES)
  self.assertEqual((lat,lng),app.PLACES["Telde"])
  self.assertEqual(a,"municipality")
 def test_precise_venue_from_independent_reference(self):
  lat,lng,a=geo.resolve("Las Palmas de Gran Canaria","Auditorio Alfredo Kraus",app.PLACES)
  self.assertEqual(a,"venue")
  self.assertNotEqual((lat,lng),app.PLACES["Las Palmas de Gran Canaria"])
  self.assertGreater(lat,27.8)
 def test_persistent_upsert_after_refresh(self):
  with sqlite3.connect(":memory:") as conn:
   conn.row_factory=sqlite3.Row
   app.init(conn)
   event={
    "title":"Concierto de prueba", "start":"2026-11-18T20:00:00","end":None,
    "municipality":"Las Palmas de Gran Canaria","venue":"Auditorio Alfredo Kraus",
    "category":"musica","free":None,"price":"","details":"Organización oficial",
    "source_name":"Fuente de prueba",
    "source_url":"https://example.org/test","status":"approved"}
   self.assertEqual(app.upsert(conn,event),"added")
   loc=conn.execute("SELECT lat,lng,accuracy FROM events").fetchone()
   self.assertEqual(loc["accuracy"],"venue")
   self.assertEqual(app.upsert(conn,event),"unchanged")
   event["venue"]="Consultar el recinto en la ficha oficial"
   self.assertEqual(app.upsert(conn,event),"unchanged")
   event["venue"]="Plaza no verificada"
   self.assertEqual(app.upsert(conn,event),"changed")
   self.assertEqual(conn.execute("SELECT accuracy FROM events").fetchone()[0],"municipality")
 def test_backfill_idempotent_and_downgrades_unknown(self):
  with sqlite3.connect(":memory:") as conn:
   conn.row_factory=sqlite3.Row
   app.init(conn)
   event={"title":"Museo de prueba","start":"2026-11-18","end":None,
          "municipality":"Las Palmas de Gran Canaria","venue":"Museo Elder",
          "category":"cultura","free":None,"price":"","details":"",
          "source_name":"Fuente de prueba","source_url":"https://example.org/test",
          "status":"approved"}
   app.upsert(conn,event)
   id=conn.execute("SELECT id FROM events").fetchone()[0]
   conn.execute("UPDATE events SET lat=?,lng=?,accuracy='municipality' WHERE id=?",
                (*app.PLACES["Las Palmas de Gran Canaria"],id))
   self.assertEqual(geo.backfill(conn,app.PLACES),1)
   self.assertEqual(geo.backfill(conn,app.PLACES),0)
   self.assertEqual(conn.execute("SELECT accuracy FROM events").fetchone()[0],"venue")
   conn.execute("UPDATE events SET venue='Recinto por confirmar' WHERE id=?",(id,))
   self.assertEqual(geo.backfill(conn,app.PLACES),1)
   self.assertEqual(conn.execute("SELECT accuracy FROM events").fetchone()[0],"municipality")
 def test_number_of_baseline_records_enriched(self):
  ev=json.loads((ROOT/"public/events.json").read_text(encoding="utf8"))["events"]
  matches=[e for e in ev if geo.find(e["municipality"],e["venue"])]
  self.assertGreaterEqual(len(matches),150)
  self.assertLess(len(matches),len(ev))
  print("BASELINE_MATCHED_RECORDS",len(matches),"BY_VENUE",
        dict(collections.Counter(x["venue"] for x in matches).most_common(12)),flush=True)

if __name__=="__main__":unittest.main()

