import sqlite3,unittest,datetime as dt,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import sync_events as app
import cross_source_venue_facts as cross

class VenueCrossSourceTests(unittest.TestCase):
 def seed(self,db,eventid,title,source,venue,date="2026-11-15",start=None):
  db.execute('''INSERT INTO events(id,dedup_key,title,start,"end",municipality,venue,category,
       free,price,details,lat,lng,accuracy,source_name,source_url,status,
       created_at,updated_at,last_seen)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
       (eventid,"id"+str(eventid),title,start or date,None,"Arucas",venue,
        "cultura",None,"","",28.119,-15.523,"municipality",source,
        "https://example.org/event/"+str(eventid),"approved","2026-10-27","2026-10-27","2026-10-27"))
 def make(self):
  c=sqlite3.connect(":memory:");c.row_factory=sqlite3.Row;app.init(c);return c
 def test_exact_title_day_different_source_one_named_venue(self):
  c=self.make()
  self.seed(c,100,"Carrera Popular","Cabildo","Consultar el recinto en la ficha oficial")
  self.seed(c,101,"Carrera Popular","Ayuntamiento de Arucas","Plaza de los Derechos Humanos")
  result=cross.enrich(c,"2026-10-27T15:00:00+00:00",dt.date(2026,10,27))
  self.assertEqual(result["verified"],1)
  self.assertEqual(c.execute("SELECT venue FROM events WHERE id=100").fetchone()[0],"Plaza de los Derechos Humanos")
 def test_different_time_or_other_event_not_enriched(self):
  c=self.make()
  self.seed(c,100,"Concierto","Cabildo","Consultar el recinto en la ficha oficial",start="2026-11-15T20:00:00")
  self.seed(c,101,"Concierto","Municipio","Auditorio de Arucas",start="2026-11-15T18:00:00")
  self.assertEqual(cross.enrich(c,"2026-10-27",dt.date(2026,10,27))["verified"],0)
 def test_ambiguous_venues_refused(self):
  c=self.make()
  self.seed(c,100,"La Barraca","Cabildo","Consultar el recinto en la ficha oficial")
  self.seed(c,101,"La Barraca","Teatro 1","Sala Insular de Teatro")
  self.seed(c,102,"La Barraca","Teatro 2","Teatro Cuyás")
  self.assertEqual(cross.enrich(c,"2026-10-27",dt.date(2026,10,27))["verified"],0)
 def test_same_source_cannot_corrobate(self):
  c=self.make()
  self.seed(c,100,"Curso infantil","Cabildo","Consultar el recinto en la ficha oficial")
  self.seed(c,101,"Curso infantil","Cabildo","Biblioteca de Arucas")
  self.assertEqual(cross.enrich(c,"2026-10-27",dt.date(2026,10,27))["verified"],0)
 def test_other_municipality_not_corrobated(self):
  c=self.make()
  self.seed(c,100,"Finaos","Cabildo","Consultar el recinto en la ficha oficial")
  self.seed(c,101,"Finaos","Ayuntamiento","Plaza de Arucas")
  c.execute("UPDATE events SET municipality='Mogán' WHERE id=101")
  self.assertEqual(cross.enrich(c,"2026-10-27",dt.date(2026,10,27))["verified"],0)
 def test_live_catalogue_sample_without_mutating_db(self):
  disk=sqlite3.connect(ROOT/"data/events.sqlite")
  mem=self.make()
  disk.backup(mem)
  disk.close()
  before=mem.execute("SELECT COUNT(*) FROM events WHERE venue LIKE 'Consultar el recinto%'").fetchone()[0]
  got=cross.enrich(mem,"2026-10-27T15:00:00+00:00",dt.date(2026,10,27))
  after=mem.execute("SELECT COUNT(*) FROM events WHERE venue LIKE 'Consultar el recinto%'").fetchone()[0]
  print("CROSSSOURCE_VERIFY_PREVIEW",got,"PLACEHOLDER_REDUCTION",before-after,flush=True)
  self.assertGreaterEqual(got["verified"],1)
  self.assertEqual(before-after,got["verified"])

if __name__=="__main__":unittest.main()
