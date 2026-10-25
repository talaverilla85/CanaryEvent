import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import municipal_listing_dedup as de
import sync_events as sync

def event(id,source,title="Festival local",start="2026-11-07",venue="",municipality="Teror",price="",image=""):
 return dict(id=id,source_name=source,title=title,start=start,municipality=municipality,venue=venue,price=price,image_url=image)
C="Portal oficial de Eventos Gran Canaria (Cabildo)"
M="Ayuntamiento de Teror · programación del Auditorio"
class MunicipalDedup(unittest.TestCase):
 def test_identical_date_title_one_visible(self):
  a=event(4,C);b=event(44,M)
  got=de.reconcile([a,b],sync.norm)
  self.assertEqual(len(got),1)
  self.assertEqual(got[0]["id"],44)
 def test_retain_verified_richer_venue_time(self):
  a=event(4,C)
  b=event(44,M,start="2026-11-07T20:30:00",venue="Auditorio de Teror",price="10 €")
  got=de.reconcile([a,b],sync.norm)
  self.assertEqual([e["id"] for e in got],[44])
 def test_preserve_two_distinct_sessions(self):
  a=event(4,C,start="2026-11-07T18:00:00")
  b=event(44,M,start="2026-11-07T20:30:00")
  self.assertEqual(len(de.reconcile([a,b],sync.norm)),2)
 def test_preserve_two_distinct_venues(self):
  a=event(4,C,venue="Plaza del Pino")
  b=event(44,M,venue="Auditorio de Teror")
  self.assertEqual(len(de.reconcile([a,b],sync.norm)),2)
 def test_preserve_nonmunicipal_events_and_different_dates(self):
  a=event(4,C)
  b=event(44,"TuReservaOnline · agenda de Gran Canaria")
  c=event(12,M,start="2026-11-08")
  self.assertEqual(len(de.reconcile([a,b,c],sync.norm)),3)
if __name__=="__main__":unittest.main()

