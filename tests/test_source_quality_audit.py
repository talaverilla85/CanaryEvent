from pathlib import Path
import sys,unittest
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import sync_events,municipal_listing_dedup as dedup,audit_source_health_gc as quality
CAB="Portal oficial de Eventos Gran Canaria (Cabildo)"
def event(id,title="Graciela Conchalovsky",start="2026-10-30T20:00:00",
          place="Teatro Cruce de Cultura",source=CAB,municipality="Agüimes"):
    return dict(id=id,title=title,start=start,venue=place,source_name=source,
                municipality=municipality,price="",free=None)
class CrossSourceVenueDedup(unittest.TestCase):
    def test_same_cabildo_event_indexed_twice(self):
        self.assertEqual(len(dedup.reconcile([event(70),event(212)],sync_events.norm)),1)
    def test_same_youth_activity_across_official_sources(self):
        v=[event(12,"Hijos de la Bruma","2026-10-30T18:00:00","La Grada",
                 "Juventud Las Palmas de Gran Canaria","Las Palmas de Gran Canaria"),
           event(220,"Hijos de la Bruma","2026-10-30T18:00:00","La Grada",
                 CAB,"Las Palmas de Gran Canaria")]
        self.assertEqual(len(dedup.reconcile(v,sync_events.norm)),1)
    def test_galdar_official_alias_but_not_arbitrary_venues(self):
        a=event(162,"Conversaciones con mi mente","2026-11-07T20:00:00",
                "Centro Cultural Guaire",CAB,"Gáldar")
        b=event(537,"Conversaciones con mi mente","2026-11-07T20:00:00",
                "Centro Cultural Guaires","Ayuntamiento de Gáldar · agenda de Cultura","Gáldar")
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),1)
        b["municipality"]="Mogán"
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),2)
    def test_known_address_suffix_is_equivalent(self):
        a=event(7,"Tributo por siempre Selena","2026-10-30T20:30:00",
                "Centro Cultural Federico García Lorca · Calle Ramón y Cajal, 29",
                "Ayuntamiento de Ingenio","Ingenio")
        b=event(214,"Tributo por siempre Selena","2026-10-30T20:30:00",
                "Centro Cultural Federico García Lorca",CAB,"Ingenio")
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),1)
    def test_official_circuit_corrects_cabildo_wrong_theatre(self):
        a=event(215,"La barraca","2026-10-30","Sala Insular de Teatro",CAB,
                "Las Palmas de Gran Canaria")
        b=event(15,"La barraca","2026-10-30T19:30:00","Teatro Cuyás",
                "Circuito de Artes Escénicas GC","Las Palmas de Gran Canaria")
        b["source_url"]="https://artesescenicasgrancanaria.com/evento-769-la-barraca-de.html"
        kept=dedup.reconcile([a,b],sync_events.norm)
        self.assertEqual([e["id"] for e in kept],[15])
    def test_official_circuit_does_not_override_different_clock(self):
        a=event(215,"La barraca","2026-10-30T21:30:00","Sala Insular de Teatro",CAB,
                "Las Palmas de Gran Canaria")
        b=event(15,"La barraca","2026-10-30T19:30:00","Teatro Cuyás",
                "Circuito de Artes Escénicas GC","Las Palmas de Gran Canaria")
        b["source_url"]="https://artesescenicasgrancanaria.com/evento-769-la-barraca-de.html"
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),2)
    def test_conflicting_venues_do_not_get_merged(self):
        a=event(215,"La barraca","2026-10-30","Sala Insular de Teatro",CAB,
                "Las Palmas de Gran Canaria")
        b=event(15,"La barraca","2026-10-30T19:30:00","Teatro Cuyás",
                "Circuito de Artes Escénicas GC","Las Palmas de Gran Canaria")
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),2)
    def test_different_sessions_or_unknown_time(self):
        a=event(1);b=event(2,start="2026-10-30T19:00:00")
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),2)
        b["start"]="2026-10-30"
        self.assertEqual(len(dedup.reconcile([a,b],sync_events.norm)),2)
    def test_nonexact_similar_place_names_do_not_merge(self):
        self.assertEqual(len(dedup.reconcile(
            [event(1,place="Teatro Cuyás"),event(2,place="Sala Insular de Teatro")],
            sync_events.norm)),2)

class SourceAuditTests(unittest.TestCase):
    def test_cabildo_idle_cycle_is_not_failure(self):
        x={"source":CAB,"found":0,"scanned":0,"skipped_recent":565,"due_urls":0,"error":""}
        self.assertEqual(quality.due_state(x),"al_dia_sin_fichas_pendientes")
        x["error"]="robots denied"
        self.assertEqual(quality.due_state(x),"error")
    def test_document_index_not_a_failed_calendar(self):
        self.assertEqual(quality.due_state({"source":"Ayuntamiento de Telde · índice de programas PDF","found":0,"error":""}),
                         "inventario_documental_no_desglosado")
    def test_quality_separates_missing_price_from_technical_errors(self):
        m={"checked_at":"2026-10-27","sources":[{"source":CAB,"found":0,"scanned":0,"due_urls":0,"skipped_recent":565,"error":""}]}
        good=[dict(title="Evento",start="2026-10-31",municipality="Telde",source_name=CAB,accuracy="municipality",price="",free=None)]
        review={"events":[dict(title="Otro evento",source_name=CAB,start="2026-11-01")]}
        report=quality.build_quality(m,good,review,{"pending_programs":[]})
        c=report["quality_counts"]
        self.assertEqual((c["publicados"],c["recintos_sin_verificar"],c["precios_sin_confirmar"],c["fuentes_con_error"]),(1,1,1,0))
        self.assertEqual(report["sources"][0]["estado"],"al_dia_sin_fichas_pendientes")

if __name__=="__main__":unittest.main()
