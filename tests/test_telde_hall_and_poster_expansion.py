"""Each confirmed Telde hall is supported by exact official event URL+date+clock."""
import datetime as dt
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_hall_venues as h
import poster_venues as p

SOURCE_URL="https://www.eventosgrancanaria.com/event/E-20261101-0003/el-lago-de-los-cisnes-international-ballet-company"
TELDE_URL="https://teldecultura.org/events/el-lago-de-los-cisnes-international-ballet-company/"
TITLE="EL LAGO DE LOS CISNES - INTERNATIONAL BALLET COMPANY"
DATE=dt.date(2026,10,28)
HTML='''<div class="card bloque-evento">
 <h4 class="em-item-title"><a href="https://teldecultura.org/events/el-lago-de-los-cisnes-international-ballet-company/">EL LAGO DE LOS CISNES - INTERNATIONAL BALLET COMPANY</a></h4>
 <span class="fechas-tarjeta">01/11/2026</span>
 <div class="em-event-time">18:00 - 19:00</div>
 </div>
<div class="card bloque-evento">
 <h4 class="em-item-title"><a href="https://attacker.example/events/other/">Other Performance</a></h4>
 <span class="fechas-tarjeta">01/11/2026</span>
 <div class="em-event-time">18:00 - 19:00</div>
 </div>'''

def database():
    con=sqlite3.connect(":memory:");con.row_factory=sqlite3.Row
    con.execute('''CREATE TABLE events (
        id INTEGER PRIMARY KEY,title TEXT,start TEXT,end TEXT,
        municipality TEXT,venue TEXT,organizer_url TEXT,
        source_url TEXT,status TEXT,updated_at TEXT)''')
    con.execute('INSERT INTO events VALUES (128,?,?,?,?,?,?,?,"approved",NULL)',
         (TITLE,"2026-11-01T18:00:00",None,"Telde",
          "Consultar el recinto en la ficha oficial",TELDE_URL,SOURCE_URL))
    return con

class TeldeVenueTests(unittest.TestCase):
    def test_matching_original_hall_programme(self):
        entries=h.parse_hall(BeautifulSoup(HTML,"html.parser"),DATE)
        self.assertEqual(len(entries),1)
        self.assertEqual(h.hall_evidence(entries,dict(database().execute("SELECT * FROM events").fetchone())),h.HALL)
    def test_no_place_for_wrong_clock_day_title_or_external_url(self):
        entries=h.parse_hall(BeautifulSoup(HTML,"html.parser"),DATE)
        original=dict(database().execute("SELECT * FROM events").fetchone())
        for altered in (
           {**original,"start":"2026-11-01T20:00:00"},
           {**original,"start":"2026-11-02T18:00:00"},
           {**original,"title":"Something else"},
           {**original,"organizer_url":"https://evil.org/events/el-lago-de-los-cisnes-international-ballet-company/"},
           {**original,"municipality":"Las Palmas de Gran Canaria"}
        ):
           self.assertEqual(h.hall_evidence(entries,altered),"")
    def test_updates_exact_matching_record_no_others(self):
        conn=database()
        conn.execute('INSERT INTO events VALUES (129,?,?,?,?,?,?,?,"approved",NULL)',
         ("Something else","2026-11-01T18:00:00",None,"Telde",
          "Consultar el recinto en la ficha oficial",TELDE_URL,SOURCE_URL))
        with patch.object(h,"_pages",return_value=iter([BeautifulSoup(HTML,"html.parser")])):
            rep=h.enrich(conn,"2026-10-28T22:00:00+00:00",DATE)
        self.assertEqual(rep["changed"],1)
        self.assertEqual(conn.execute("SELECT venue FROM events WHERE id=128").fetchone()[0],h.HALL)
        self.assertEqual(conn.execute("SELECT venue FROM events WHERE id=129").fetchone()[0],"Consultar el recinto en la ficha oficial")
    def test_poster_accepts_unique_main_title_without_producer_suffix(self):
        event={"title":TITLE,"start":"2026-11-01T18:00:00","municipality":"Telde"}
        obj={"one_event_single_venue":True,"poster_title":"EL LAGO DE LOS CISNES",
             "date_text":"1 noviembre 2026",
             "venue":"Teatro Municipal Juan Ramón Jiménez",
             "venue_evidence":"TEATRO MUNICIPAL JUAN RAMÓN JIMÉNEZ"}
        self.assertEqual(p.check_reading(obj,event),obj["venue"])
        self.assertEqual(p.agreement(obj,dict(obj),event),obj["venue"])
        self.assertEqual(p.check_reading({**obj,"poster_title":"Cenicienta"},event),"")
        self.assertEqual(p.check_reading({**obj,"date_text":"2 noviembre 2026"},event),"")
    def test_bad_external_domain_rejected(self):
        self.assertFalse(h.event_url("https://teldecultura.org.evil.example/events/lago/"))
        self.assertFalse(h.event_url("http://teldecultura.org/events/lago/"))
        self.assertFalse(h.event_url(TELDE_URL+"?redirect=bad"))

if __name__=="__main__": unittest.main()
