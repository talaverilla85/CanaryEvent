"""A Cabildo sister-site URL is NOT proof of Sala Insular as a venue."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import cuyas_corroboration as cy

BARRACA="LA BARRACA de Vicente Blasco Ibáñez"
ESCAPE="ESCAPE ROOM de Joel Joan y Hèctor Claramunt"
ORIGINAL_B="https://artesescenicasgrancanaria.com/evento-769-la-barraca-de.html"
ORIGINAL_E="https://teatrocuyas.com/evento-772-escape-room-de.html"
DUP_B="https://salainsulardeteatro.com/evento-769-la-barraca-de.html"
DUP_E="https://salainsulardeteatro.com/evento-772-escape-room-de.html"
CITY="Las Palmas de Gran Canaria"

def item(id,title,start,source,uri,venue,organizer="",end=None,city=CITY):
    return {"id":id,"title":title,"start":start,"end":end,
            "municipality":city,"venue":venue,"source_name":source,
            "source_url":uri,"organizer_url":organizer}

def db():
    con=sqlite3.connect(":memory:");con.row_factory=sqlite3.Row
    con.execute('''CREATE TABLE events (
      id INTEGER PRIMARY KEY,title TEXT,start TEXT,end TEXT,
      municipality TEXT,venue TEXT,source_name TEXT,source_url TEXT,
      organizer_url TEXT,status TEXT,updated_at TEXT)''')
    return con

def put(con,e):
    con.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,'approved',NULL)",
            tuple(e[k] for k in ("id","title","start","end","municipality","venue",
                       "source_name","source_url","organizer_url")))

def corpus():
    primary="Teatro Cuyás · agenda oficial"
    copy="Portal oficial de Eventos Gran Canaria (Cabildo)"
    rows=[
      item(15,BARRACA,"2026-10-30T19:30:00","Circuito de Artes Escénicas GC",ORIGINAL_B,"Teatro Cuyás"),
      item(16,BARRACA,"2026-10-31T19:30:00","Circuito de Artes Escénicas GC",ORIGINAL_B,"Teatro Cuyás"),
      item(218,BARRACA,"2026-10-30",copy,"https://www.eventosgrancanaria.com/event/E-20261030-0023/la-barraca-de-vicente-blasco-ibanez",
          "Consultar el recinto en la ficha oficial",DUP_B,"2026-10-31"),
      item(695,ESCAPE,"2026-11-20T19:30:00",primary,ORIGINAL_E,"Teatro Cuyás"),
      item(696,ESCAPE,"2026-11-21T19:30:00",primary,ORIGINAL_E,"Teatro Cuyás"),
      item(286,ESCAPE,"2026-11-20",copy,"https://www.eventosgrancanaria.com/event/E-20261120-0015/escape-room",
          "Consultar el recinto en la ficha oficial",DUP_E,"2026-11-21"),
      item(215,BARRACA,"2026-10-30",copy,"https://www.eventosgrancanaria.com/event/E-20261030-0012/la-barraca",
           "Sala Insular de Teatro",end="2026-10-31"),
      item(282,ESCAPE,"2026-11-20",copy,"https://www.eventosgrancanaria.com/event/E-20261120-0008/escape-room",
           "Sala Insular de Teatro",end="2026-11-22"),
    ]
    return rows

class CuyasCorroborationTests(unittest.TestCase):
    def test_same_official_show_id_title_full_day_span(self):
        c=db()
        for row in corpus():put(c,row)
        result=cy.enrich(c,"2026-10-28",dt.date(2026,10,28))
        self.assertEqual(result["changed"],2)
        self.assertEqual(c.execute("SELECT venue FROM events WHERE id=218").fetchone()[0],"Teatro Cuyás")
        self.assertEqual(c.execute("SELECT venue FROM events WHERE id=286").fetchone()[0],"Teatro Cuyás")
        again=cy.enrich(c,"2026-10-28",dt.date(2026,10,28))
        self.assertEqual(again["changed"],0)

    def test_do_not_guess_if_event_id_or_full_date_set_disagrees(self):
        primary=[x for x in corpus() if x["id"] in (15,16,695,696)]
        groups={}
        for row in primary:
            import re
            n=re.search(r"evento-(\d+)",row["source_url"]).group(1)
            groups.setdefault(n,[]).append(row)
        baseline=[x for x in corpus() if x["id"]==218][0]
        for replacement in (
            {"organizer_url":"https://salainsulardeteatro.com/evento-777-la-barraca-de.html"},
            {"title":"LA BARRACA de otra compañía"},
            {"municipality":"Telde"},
            {"end":"2026-11-01"},
            {"start":"2026-10-31","end":"2026-10-31"},
            {"start":"2026-10-30T21:00:00"},
            {"organizer_url":"https://salainsulardeteatro.com.evil.example/evento-769-la-barraca-de.html"},
        ):
            self.assertEqual(cy.corroborate(groups,{**baseline,**replacement}),"",replacement)
        self.assertEqual(cy.corroborate(groups,baseline),"Teatro Cuyás")

    def test_sister_theatre_conflicts_quarantined_not_new_phantom_date(self):
        events=corpus()
        kept,problems=cy.exclude_conflicting_sister_venue(events)
        self.assertEqual({x["id"] for x in problems},{215,282})
        self.assertNotIn(282,{x["id"] for x in kept})
        self.assertIn(218,{x["id"] for x in kept})
        self.assertEqual({x["id"] for x in kept if x["id"] in (15,16,695,696)},
                         {15,16,695,696})
        self.assertTrue(all(x["reason"]=="conflicting_sister_theatre" for x in problems))

    def test_sister_stage_does_not_hide_unrelated_performance(self):
        examples=corpus()
        other=next(x for x in examples if x["id"]==282).copy()
        other["id"]=701
        other["title"]="Escape Room: diferente obra"
        extra=next(x for x in examples if x["id"]==215).copy()
        extra["id"]=702
        extra["municipality"]="Telde"
        kept,problems=cy.exclude_conflicting_sister_venue(examples+[other,extra])
        self.assertEqual({x["id"] for x in problems},{215,282})
        self.assertTrue({701,702}.issubset({x["id"] for x in kept}))

if __name__=="__main__":
    unittest.main()
