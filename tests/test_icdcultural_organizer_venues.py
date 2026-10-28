"""Event-specific organizer venue, not the organizer's own theatre address."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import organizer_venues as ov
import structured_organizer_venues as s
import sync_events as app

URL="https://cultura.icdcultural.org/programacion-guiniguada/taller-de-danza-iniciacion-al-tarantismo-y-la-pizzica"
TITLE='Taller de danza "Iniciación al tarantismo y la pizzica"'
EXPECTED="Gimnasio del aulario de Santa Teresa del Campus del Obelisco de la ULPGC"
SOURCE_TEXT=(
    "En paralelo a la función de 'Quiso Negro', Esther Gutin ofrece un taller de danza. "
    "La sede del taller será el gimnasio del aulario de Sta. Teresa "
    "del Campus del Obelisco de la ULPGC. La actividad forma parte del "
    "proyecto Bailar los campus en colaboración con el Teatro Guiniguada. "
    "Horario: 17:00"
)
def html(*,date="30/10/2026",text=SOURCE_TEXT,title=TITLE):
    return f'''<html><body><h1>{title}</h1>
    <div class="text-block-323">{date}</div>
    <div class="div-block-527"><div class="w-richtext"><p>{text}</p></div></div>
    <footer>Teatro Guiniguada, Las Palmas de Gran Canaria</footer></body></html>'''

class OrganizerVenueTextTests(unittest.TestCase):
    def test_finds_actual_offsite_hall_not_organizing_theatre(self):
        soup=BeautifulSoup(html(),"html.parser")
        self.assertTrue(ov.title_matches(soup,TITLE))
        self.assertEqual(s.extract(soup,URL,"Las Palmas de Gran Canaria","2026-10-30","17:00"),EXPECTED)
        self.assertNotIn("Guiniguada",EXPECTED)

    def test_event_date_and_clock_both_required(self):
        soup=BeautifulSoup(html(),"html.parser")
        self.assertEqual(s.extract(soup,URL,"Las Palmas de Gran Canaria","2026-10-31","17:00"),"")
        self.assertEqual(s.extract(soup,URL,"Las Palmas de Gran Canaria","2026-10-30","18:00"),"")
        self.assertEqual(s.extract(soup,URL,"Telde","2026-10-30","17:00"),"")
        self.assertEqual(s.extract(BeautifulSoup(html(date="31/10/2026"),"html.parser"),
                    URL,"Las Palmas de Gran Canaria","2026-10-30","17:00"),"")

    def test_organizer_reference_or_footer_is_not_venue(self):
        sample=html(text="Esta actividad forma parte de la programación del Teatro Guiniguada. Horario: 17:00")
        self.assertEqual(s.extract(BeautifulSoup(sample,"html.parser"),
                         URL,"Las Palmas de Gran Canaria","2026-10-30","17:00"),"")
        sample=html(text="El Teatro Guiniguada coordina el taller. La sede está aún por confirmar. Horario: 17:00")
        self.assertEqual(s.extract(BeautifulSoup(sample,"html.parser"),
                         URL,"Las Palmas de Gran Canaria","2026-10-30","17:00"),"")

    def test_conflicting_places_rejected(self):
        sample=html(text=("La sede del taller será el gimnasio del aulario de Sta. Teresa "
             "del Campus del Obelisco de la ULPGC. "
             "La sede del taller será el Museo Elder. Horario: 17:00"))
        self.assertEqual(s.extract(BeautifulSoup(sample,"html.parser"),
                         URL,"Las Palmas de Gran Canaria","2026-10-30","17:00"),"")

    def test_verification_versions_invalidate_negative_cache(self):
        self.assertIn("v3",ov.PARSER_VERSION)
        self.assertIn("cultura.icdcultural.org",s.SUPPORTED_HOSTS)
        self.assertTrue(ov.valid_url(URL))
        self.assertFalse(ov.valid_url("https://cultura.icdcultural.org.evil.example/test"))

    def test_actual_db_row_still_eligible_for_updated_parser(self):
        with sqlite3.connect(str(ROOT/"data/events.sqlite")) as conn:
            conn.row_factory=sqlite3.Row
            row=conn.execute("SELECT * FROM events WHERE id=99").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["organizer_url"],URL)
            self.assertEqual(row["start"][:16],"2026-10-30T17:00")
            self.assertFalse(row["venue"]==EXPECTED)

if __name__=="__main__":unittest.main()
