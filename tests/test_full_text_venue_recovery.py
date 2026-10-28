import datetime as dt
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from bs4 import BeautifulSoup
import cabildo_public as cabildo
import official_address_locations as addresses
import source_facts
import sync_events as app

LIBRARY_URL="https://www.eventosgrancanaria.com/event/E-20261030-0030/taller-infantil-reposteria-encantada"
BOOK_URL="https://www.eventosgrancanaria.com/event/E-20261029-0013/presentacion-del-libro-con-sal-en-la-memoria-de-mar-zeraus"
DATE=dt.date(2026,10,28)
START_NOW="2026-10-28T22:45:00+00:00"
LIBRARY_DESCRIPTION=(
 "Viernes 30 octubre 2026 · 16:30 y 18:30 h Por La Cocinita Cupcakes "
 "Cada participante decorará dos cupcakes y dos galletas de Halloween. "
 "Para edades de 7 a 9 años (en la sesión de las 16:30 h) y de "
 "10 a 13 años (en la sesión de las 18:30 h). Taller gratuito. "
 "Plazas limitadas. Inscripción por correo electrónico a la Biblioteca. "
 "+Información: http://bibliotecainsular.grancanaria.com "
 "Biblioteca Insular de Gran Canaria Remedios, 7 35002. "
 "Las Palmas de Gran Canaria Tel. 928 382 672"
)
BOOK_DESCRIPTION=("Jueves 29 octubre 2026 · 19:00 h. Presentación del libro. "
                  "Actividad gratuita. Más información: www.tomasmorales.com "
                  "Casa-Museo Tomás Morales Plaza Tomás Morales, s/n. 35420. Moya")

def event_page(title,day,municipality,description):
    schema={"@type":"Event","location":{"name":municipality},
            "description":description[:500]}
    return ('''<html><h1 class="event-detail__title">'''+title+'''</h1>
      <div class="event-detail__details-list">
        <p class="event-detail__text">'''+municipality+'''</p>
        <p class="event-detail__text">'''+day+'''</p>
      </div>
      <div id="info-panel"><p class="event-detail__text">'''+description+'''</p></div>
      <script type="application/ld+json">'''+json.dumps(schema,ensure_ascii=False)+'''</script></html>''')

class RecoverFullDescription(unittest.TestCase):
    def test_official_address_signatures_require_city_street_and_postcode(self):
        self.assertEqual(addresses.from_official_address(LIBRARY_DESCRIPTION,"Las Palmas de Gran Canaria"),
                         "Biblioteca Insular de Gran Canaria")
        self.assertEqual(addresses.from_official_address(BOOK_DESCRIPTION,"Moya"),
                         "Casa-Museo Tomás Morales")
        self.assertEqual(addresses.from_official_address(
            LIBRARY_DESCRIPTION.replace("Remedios, 7","Remedios, 8"),"Las Palmas de Gran Canaria"),"")
        self.assertEqual(addresses.from_official_address(
            LIBRARY_DESCRIPTION.replace("35002","35003"),"Las Palmas de Gran Canaria"),"")
        self.assertEqual(addresses.from_official_address(LIBRARY_DESCRIPTION,"Mogán"),"")
        self.assertEqual(addresses.from_official_address(
            "Biblioteca Insular de Gran Canaria colabora en el taller","Las Palmas de Gran Canaria"),"")

    def test_full_text_beyond_clipped_jsonld_recovers_workshop(self):
        page=event_page("Taller infantil: Repostería encantada","30/10/2026",
                        "Las Palmas de Gran Canaria",LIBRARY_DESCRIPTION)
        entry=cabildo.extract_factual_event(page,LIBRARY_URL,DATE,app.PLACES,app.norm,app.category)
        self.assertEqual(entry["venue"],"Biblioteca Insular de Gran Canaria")
        self.assertEqual(entry["start"],"2026-10-30T16:30:00")
        self.assertIsNone(entry["end"])
        self.assertIn("18:30",entry["details"])
        self.assertEqual(entry["free"],1)
        self.assertEqual(entry["price"],"Gratis")

    def test_book_presentation_in_moya(self):
        page=event_page("Presentación del libro Con sal en la memoria",
                        "29/10/2026","Moya",BOOK_DESCRIPTION)
        event=cabildo.extract_factual_event(page,BOOK_URL,DATE,app.PLACES,app.norm,app.category)
        self.assertEqual(event["venue"],"Casa-Museo Tomás Morales")
        self.assertEqual(event["price"],"Gratis")
        # Single-session hour is not parsed from registration text by guessing.
        self.assertEqual(event["start"],"2026-10-29")

    def test_different_sessions_not_fake_continuous_event(self):
        self.assertEqual(source_facts.separate_sessions(LIBRARY_DESCRIPTION)[0],"16:30")
        self.assertEqual(source_facts.separate_sessions("Inscripciones de 16:30 a 18:30 h"),(None,""))
        self.assertEqual(source_facts.separate_sessions("16:30 y 18:30 h. Taller de dos días"),(None,""))
        self.assertEqual(source_facts.separate_sessions(""),(None,""))

    def test_legacy_scanned_url_is_refreshed_once_without_fetching_all(self):
        sample=event_page("Taller infantil: Repostería encantada",
                          "30/10/2026","Las Palmas de Gran Canaria",LIBRARY_DESCRIPTION)
        urls=[f"https://www.eventosgrancanaria.com/event/E-20261030-{i:04d}/actividad" for i in range(25)]
        urls[0]=LIBRARY_URL
        class Response:
            content=sample.encode("utf-8")
            headers={"content-type":"text/html"}
            status_code=200
            def raise_for_status(self):pass
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory=sqlite3.Row
            app.init(conn)
            event={"title":"Taller infantil: Repostería encantada",
                   "start":"2026-10-30","end":None,
                   "municipality":"Las Palmas de Gran Canaria",
                   "venue":"Consultar el recinto en la ficha oficial",
                   "category":"familia","free":None,"price":"","details":"",
                   "source_name":cabildo.SOURCE_NAME,
                   "source_url":LIBRARY_URL,"status":"approved"}
            app.upsert(conn,event)
            conn.execute("""CREATE TABLE cabildo_scans(url TEXT PRIMARY KEY,
                checked_at TEXT NOT NULL,outcome TEXT NOT NULL,
                image_inspected INTEGER NOT NULL,facts_inspected INTEGER NOT NULL,
                venue_inspected INTEGER NOT NULL)""")
            conn.executemany("INSERT INTO cabildo_scans VALUES(?,?,?,1,1,1)",
                             [(u,START_NOW,"valid") for u in urls])
            with patch.object(cabildo,"scan_allowed"),patch.object(cabildo,"list_public_events",
                  return_value=[(u,dt.date(2026,10,30)) for u in urls]),patch.object(cabildo.SESSION,"get",return_value=Response()) as get,patch.object(cabildo.time,"sleep"):
                report=cabildo.synchronize(conn,START_NOW,DATE,app.PLACES,
                        app.norm,app.category,app.upsert,max_pages=1)
            self.assertEqual(report["scanned"],1)
            self.assertEqual(report["pending_full_text_rechecks"],1)
            get.assert_called_once()
            self.assertEqual(get.call_args.args[0],LIBRARY_URL)
            row=conn.execute("SELECT venue,start FROM events WHERE source_url=?",(LIBRARY_URL,)).fetchone()
            self.assertEqual(row["venue"],"Biblioteca Insular de Gran Canaria")
            self.assertEqual(row["start"],"2026-10-30T16:30:00")
            self.assertEqual(conn.execute("SELECT full_text_v2 FROM cabildo_scans WHERE url=?",
                                           (LIBRARY_URL,)).fetchone()[0],1)

if __name__=="__main__":unittest.main()
