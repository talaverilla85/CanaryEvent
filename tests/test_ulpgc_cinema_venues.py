"""Official 2026 ULPGC cine corroboration, isolated from other university events."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import ulpgc_cinema_venues as u

TITLE_PREFIX="Aula de cine. Ciclo “Los modernos años 30”. "
TITLES={
"2026-10-30":"El ángel azul",
"2026-11-06":"Asesinato",
"2026-11-13":"M. El vampiro de Düsseldorf",
"2026-11-20":"Viva la libertad",
"2026-11-27":"Scarface, El Terror del Hampa",
"2026-12-04":"Ámame esta noche",
"2026-12-11":"Una mujer fuera de la ley",
"2026-12-18":"La mujer de todos",
}
SOURCE="https://www.eventosgrancanaria.com/event/E-20261030-0006/aula-de-cine-ciclo"
ORGANIZER="https://www.ulpgc.es/agenda/2026/10/30/aula-cine"
OFFICIAL_HTML="""<html><head><title>Cine en la ULPGC para el segundo semestre del año</title></head>
<body><main><h1>Cine en la ULPGC para el segundo semestre del año</h1>
<p>Del 23 de octubre al 18 de diciembre es el turno de Los modernos, nueve películas.
Son, por orden cronológico: Aleluya, El ángel azul, Asesinato,
M, el vampiro de Düsserldorf, Viva la libertad,
Scarface, el terror del hampa, Ámame este noche,
Una mujer fuera de la ley y La mujer de todos.
Las proyecciones tendrán lugar a las 19:00 en el Salón de Actos del Edificio de Humanidades.</p>
</main><footer>Biblioteca Tafira, avenida de la Universidad</footer></body></html>"""

def event(day,film,**updates):
    x={"title":TITLE_PREFIX+film,"start":day+"T19:00:00",
       "municipality":"Las Palmas de Gran Canaria","venue":"Consultar el recinto en la ficha oficial",
       "source_url":SOURCE,"organizer_url":ORGANIZER}
    x.update(updates)
    return x

def db():
    c=sqlite3.connect(":memory:");c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE events (
      id INTEGER PRIMARY KEY,title TEXT,start TEXT,end TEXT,
      municipality TEXT,venue TEXT,source_url TEXT,organizer_url TEXT,
      status TEXT,updated_at TEXT)''')
    for i,(day,film) in enumerate(TITLES.items(),start=100):
        e=event(day,film)
        if i%2==0:e["start"]=day  # Cabildo sometimes records only the day.
        c.execute('''INSERT INTO events(id,title,start,municipality,venue,source_url,
                  organizer_url,status) VALUES(?,?,?,?,?,?,?,'approved')''',
                  (i,e["title"],e["start"],e["municipality"],e["venue"],e["source_url"],e["organizer_url"]))
    return c

class FilmCycleTests(unittest.TestCase):
    def test_direct_official_article_confirms_exact_venue(self):
        self.assertTrue(u.verified_article_text(OFFICIAL_HTML))
        bad=OFFICIAL_HTML.replace("Salón de Actos del Edificio de Humanidades","Teatro Guiniguada")
        self.assertFalse(u.verified_article_text(bad))
        bad=OFFICIAL_HTML.replace("Del 23 de octubre al 18 de diciembre","Durante este curso")
        self.assertFalse(u.verified_article_text(bad))
        bad=OFFICIAL_HTML.replace("La mujer de todos","Otra película")
        self.assertFalse(u.verified_article_text(bad))

    def test_only_2026_listed_titles_and_correct_source_and_clock(self):
        for day,film in TITLES.items():
            self.assertTrue(u.event_qualifies(event(day,film)))
            self.assertTrue(u.event_qualifies(event(day,film,start=day)))
        orig=event("2026-10-30","El ángel azul")
        for extra in (
           {"start":"2026-10-30T20:00:00"},
           {"start":"2027-10-30T19:00:00"},
           {"municipality":"Mogán"},
           {"venue":"Teatro Guiniguada"},
           {"organizer_url":"https://www.ulpgc.es/agenda/2025/unrelated"},
           {"source_url":"https://example.com/event/20261030"},
           {"title":"Concierto Aula de Cine: El ángel azul"},
           {"title":"Aula de cine. Ciclo “Decálogo”. El ángel azul"},
        ):
            self.assertFalse(u.event_qualifies({**orig,**extra}),extra)

    def test_populates_eight_verified_events_once_and_only_once(self):
        c=db()
        with patch.object(u,"download_article",return_value=u.verified_article_text(OFFICIAL_HTML)) as fetch:
            report=u.enrich(c,"2026-10-28T23:45:00+00:00",dt.date(2026,10,28))
            self.assertEqual(report["changed"],8)
            self.assertEqual(report["eligible"],8)
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM events WHERE venue=?",(u.HALL,)).fetchone()[0],8)
            again=u.enrich(c,"2026-10-28T23:45:00+00:00",dt.date(2026,10,28))
            self.assertEqual(again["changed"],0)

    def test_missing_or_unverified_source_never_releases_event(self):
        c=db()
        with patch.object(u,"download_article",return_value=""):
            out=u.enrich(c,"2026-10-28",dt.date(2026,10,28))
        self.assertEqual(out["changed"],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM events WHERE venue=?",(u.HALL,)).fetchone()[0],0)
        self.assertEqual(out["error"],"ValueError")

if __name__=="__main__":unittest.main()
