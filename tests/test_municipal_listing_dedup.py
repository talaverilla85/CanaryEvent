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
 def test_artenara_market_is_same_event_despite_shorter_name(self):
  cab=event(2,C,title="II Edición del Mercadillo Tradicional de Artenara",
            start="2026-10-31",municipality="Artenara")
  mun=event(3,"Ayuntamiento de Artenara · ferias tradicionales 2026",
            title="II Mercadillo Tradicional · Artenara",
            start="2026-10-31",municipality="Artenara")
  self.assertEqual(len(de.reconcile([cab,mun],sync.norm)),1)
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


class IngenioCabildoDedupRegression(unittest.TestCase):
 def test_same_event_known_same_venue_single_public_card(self):
  a=dict(id=501,title="MARTA BOLAÑOS EN ACÚSTICO",
         start="2026-10-29",municipality="Ingenio",
         venue="Fundación Nanino Diáz Cutillas · C/ Obispo Manjón, 14",
         source_name="Portal oficial de Eventos Gran Canaria (Cabildo)",
         source_url="https://www.eventosgrancanaria.com/event/E-20261029-0001/marta",price="",free=None)
  b=dict(a,id=502,start="2026-10-29T19:00:00",
         source_name="Ayuntamiento de Ingenio",
         source_url="https://ingenio.es/events/marta-bolanos/")
  self.assertEqual(len(de.reconcile([a,b],sync.norm)),1)
  self.assertEqual(de.reconcile([a,b],sync.norm)[0]["id"],502)
 def test_compatible_location_but_different_hours_not_merged(self):
  a=dict(id=501,title="Concierto",start="2026-11-29T17:00:00",
         municipality="Ingenio",venue="Centro Cultural Federico García Lorca",
         source_name="Portal oficial de Eventos Gran Canaria (Cabildo)",
         source_url="https://example.org/cabildo",free=None,price="")
  b=dict(a,id=502,start="2026-11-29T20:00:00",source_name="Ayuntamiento de Ingenio",
         source_url="https://ingenio.es/events/concierto/")
  self.assertEqual(len(de.reconcile([a,b],sync.norm)),2)
