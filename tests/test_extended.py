import datetime as dt
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_events as app

class ExtendedTests(unittest.TestCase):
    def test_time_changes_keep_same_event_id(self):
        with sqlite3.connect(":memory:") as c:
            c.row_factory=sqlite3.Row
            app.init(c)
            e={"title":"Taller Artesanía","start":app.TODAY.isoformat()+"T16:00:00","end":None,
               "municipality":"Ingenio","venue":"Sala A","category":"cultura","free":None,
               "price":"","details":"","source_name":"Fuente municipal",
               "source_url":"https://ingenio.es/events/test","status":"approved"}
            self.assertEqual(app.upsert(c,e),"added")
            id_before=c.execute("SELECT id FROM events").fetchone()[0]
            e["start"]=app.TODAY.isoformat()+"T17:00:00"
            self.assertEqual(app.upsert(c,e),"changed")
            self.assertEqual(c.execute("SELECT id FROM events").fetchone()[0],id_before)
            e["title"]="CANCELADO: Taller Artesanía"
            e["status"]="cancelled"
            self.assertEqual(app.upsert(c,e),"changed")
            self.assertEqual(c.execute("SELECT COUNT(*) FROM events").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT status FROM events").fetchone()[0],"cancelled")

    def test_two_official_sessions_same_title_and_date_are_distinct(self):
        a={"title":"Cine","start":app.TODAY.isoformat()+"T19:00:00","municipality":"Telde",
           "source_url":"https://www.eventosgrancanaria.com/event/E-20261024-0001/cine"}
        b={**a,"source_url":"https://www.eventosgrancanaria.com/event/E-20261024-0002/cine"}
        self.assertNotEqual(app.dedup_key(a),app.dedup_key(b))

    def test_official_ingenio_cancelled_schema(self):
        d=app.TODAY
        month=[k for k,v in app.MONTHS.items() if v==d.month and len(k)==3][0]
        url="https://ingenio.es/events/taller-test/"
        ld={"@type":"Event","eventStatus":"https://schema.org/EventCancelled","offers":{"url":url}}
        html=f'''<script type="application/ld+json">{json.dumps(ld)}</script>
        <article class="mec-event-article mec-toggle-{d:%Y%m}-901">
        <h3 class="mec-event-title"><a href="{url}">Taller Creativo</a></h3>
        <span class="mec-start-date-label">{d.day} {month}</span>
        <span class="mec-start-time">16:00</span>
        <div class="mec-venue-details"><span>Centro Cultural</span></div></article>'''
        e=app.extract_ingenio(BeautifulSoup(html,"html.parser"))
        self.assertEqual(len(e),1)
        self.assertEqual(e[0]["status"],"cancelled")

    def test_artes_each_dated_session(self):
        d=app.TODAY+dt.timedelta(days=3)
        date=d.strftime("%d/%m/%Y")
        html=f'''<div class="agenda_evento">
        <div class="agenda_tituloevento">La Barraca</div>
        <div class="calendar_zonaevento">Las Palmas de Gran Canaria, Teatro Cuyás</div>
        <a href="evento-769-la-barraca-de.html">Enlace</a>
        <table class="mtable"><tr><td><div class="left">{date}</div></td><td>19:30</td></tr></table>
        </div>'''
        e=app.extract_artes(BeautifulSoup(html,"html.parser"))
        self.assertEqual(len(e),1)
        self.assertEqual(e[0]["municipality"],"Las Palmas de Gran Canaria")
        self.assertEqual(e[0]["start"][:10],d.isoformat())

if __name__=="__main__":unittest.main()
