import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import official_venue_confirmations as o
import venue_title_variants as aliases
import cross_source_venue_facts as cross
import venue_quality as v

class VenueCorroborationTests(unittest.TestCase):
    def test_official_matching_is_allowlisted(self):
        fake=type("Session",(),{"get":lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("network"))})()
        with self.assertRaises(ValueError):
            o.fetch_official(fake,"https://example.com/unrelated")

    def test_corroboration_requires_visible_named_place(self):
        with patch.object(o,"fetch_official",return_value="not relevant"):
            db=sqlite3.connect(":memory:")
            db.row_factory=sqlite3.Row
            db.execute("CREATE TABLE events(id INTEGER PRIMARY KEY,title TEXT,municipality TEXT,venue TEXT,source_url TEXT,start TEXT, status TEXT, updated_at TEXT, end TEXT)")
            fact=o.FACTS[0]
            db.execute("INSERT INTO events(id,title,municipality,venue,source_url,start,status) VALUES(1,?,?,?,?,?,'approved')",
                       (fact["title"],fact["municipality"],"Consultar el recinto en la ficha oficial",
                        "https://www.eventosgrancanaria.com/event/E-20261009-0036/oliva-lara-ultimo-pintor-indigenista-americano",
                        "2026-10-27"))
            result=o.enrich(db,"2026-10-27",dt.date(2026,10,27))
            self.assertEqual(result["updated"],0)
            self.assertEqual(db.execute("SELECT venue FROM events WHERE id=1").fetchone()[0],
                             "Consultar el recinto en la ficha oficial")
            good=" ".join(fact["tokens"])
            with patch.object(o,"fetch_official",return_value=o.normalized(good)):
                result=o.enrich(db,"2026-10-27",dt.date(2026,10,27))
            self.assertEqual(result["updated"],1)
            self.assertEqual(db.execute("SELECT venue FROM events WHERE id=1").fetchone()[0],
                             "Museo Agáldar de Historia de la Ciudad")

    def test_aliases_not_fuzzy_and_dont_equate_unrelated_titles(self):
        self.assertTrue(aliases.variants("Noche de Tapas · San Rafael") &
                        aliases.variants("Noche de Tapas"))
        self.assertTrue(aliases.variants("AL VACÍO - TELDE") &
                        aliases.variants("AL VACÍO"))
        self.assertTrue(aliases.variants("Concierto: Marta Bolaños en acústico") &
                        aliases.variants("Marta Bolaños en acústico"))
        self.assertFalse(aliases.variants("La Barraca") &
                         aliases.variants("El libro de la Barraca"))
        self.assertFalse(aliases.variants("Fiestas San Rafael") &
                         aliases.variants("Noche de Tapas San Rafael"))
if __name__=="__main__":
    unittest.main()
