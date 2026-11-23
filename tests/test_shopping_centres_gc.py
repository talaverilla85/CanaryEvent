"""Official retail-centre events must be dated, unique and never advertising."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shopping_centres_gc as malls
import verified_venue_coordinates as coords

FIXTURE = """
<article>
<h1>Club Arenillo: programación Navidad 🎄</h1>
<p>NOVIEMBRE</p>
<p>Taller de bloques de construcción, horario de 17:00 a 20:00</p>
<ul><li>Viernes 21 de 17:00 a 20:00 h – Taller de bloques</li>
<li>Jueves 26</li><li>Viernes 27</li></ul>
<p>DICIEMBRE</p>
<ul>
<li>Viernes 4 de 17:00 a 20:00 h – Taller tazas de cacao</li>
<li>Sábado 5 de 11:00 a 14:00 h y de 17:00 a 20:00 h. – Taller de muñecos de nieve</li>
<li>Jueves 10 de 17:00 a 20:00 h – Rebajas Black Friday</li>
</ul>
<p>ENERO</p>
<ul><li>Sábado 2 de 17:00 a 20:00 h – GRAN RECEPCIÓN DE LOS REYES MAGOS</li></ul>
<p>Tren de renos del Polo Norte 🦌🚂</p>
<p>Diciembre:</p><ul>
<li>Del jueves 3 al sábado 5</li>
<li>Del viernes 18 al domingo 20</li></ul>
<p>Enero:</p>
<ul><li>Del sábado 2 al lunes 4</li></ul>
</article>
"""


class ChristmasShoppingCentreTests(unittest.TestCase):
    def parse(self, html=FIXTURE, today=dt.date(2026, 11, 23)):
        return malls.extract_las_arenas(BeautifulSoup(html,"html.parser"),today,2026)

    def test_explicit_sessions_and_trains_and_year_boundary(self):
        result=self.parse()
        titles={e["title"] for e in result}
        self.assertIn("Taller tazas de cacao · Navidad en Las Arenas",titles)
        self.assertIn("GRAN RECEPCIÓN DE LOS REYES MAGOS · Navidad en Las Arenas",titles)
        self.assertEqual(len(result),14)
        self.assertTrue(all("2026-11-21" not in e["start"] for e in result))
        self.assertTrue(any(e["start"]=="2027-01-04T17:00:00" for e in result))
        self.assertTrue(all(e["free"] is None and e["price"]=="" for e in result))
        self.assertTrue(all(e["source_url"]==malls.official_url(2026) for e in result))
        self.assertTrue(all("Horario anunciado" in e["details"] for e in result))
        self.assertTrue(all("para público infantil y familiar" in e["details"] for e in result))
        self.assertEqual(len({(e["title"],e["start"][:10]) for e in result}),len(result))

    def test_weekday_mismatch_is_not_reinterpreted_as_different_year(self):
        items=self.parse()
        self.assertFalse(any(e["start"][:10]=="2026-11-21" for e in items))
        self.assertTrue(any(e["start"][:10]=="2026-11-26" for e in items))

    def test_two_periods_are_explicit_not_assumed_continuous(self):
        e=next(e for e in self.parse() if e["title"].startswith("Taller de muñecos"))
        self.assertEqual(e["start"],"2026-12-05T11:00:00")
        self.assertIn("11:00–14:00, 17:00–20:00", e["details"])

    def test_rejects_undated_shopping_offers_and_untrusted_umbrella_pages(self):
        bad=FIXTURE.replace("Club Arenillo: programación Navidad", "Ofertas Black Friday")
        self.assertEqual(self.parse(bad), [])
        self.assertFalse(any("rebajas" in e["title"].casefold() for e in self.parse()))
        # The adapter is intentionally confined to Club Arenillo; it never
        # tries to scrape unrelated store or retail promotional articles.

    def test_no_stale_season_republication(self):
        self.assertIsNone(malls.season_for(dt.date(2027,2,1)))
        self.assertEqual(malls.season_for(dt.date(2027,1,3)),2026)
        self.assertEqual(malls.season_for(dt.date(2026,11,23)),2026)
        self.assertEqual(self.parse(today=dt.date(2027,1,5)),[])

    def test_coordinates_are_verified_venue_specific(self):
        place=coords.find("Las Palmas de Gran Canaria",malls.VENUE)
        self.assertTrue(place)
        self.assertAlmostEqual(place[0],28.12826,places=4)

    def test_daily_synchronizer_keeps_ingestion_isolated_and_source_audited(self):
        conn=sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE source_log(
          source TEXT PRIMARY KEY,checked_at TEXT,found INTEGER DEFAULT 0,
          added INTEGER DEFAULT 0,changed INTEGER DEFAULT 0,error TEXT)""")
        saved={}
        def upsert(_conn,event):
            key=(event["title"],event["start"][:10])
            previous=key in saved
            saved[key]=event
            return "unchanged" if previous else "added"
        fetch=lambda url:BeautifulSoup(FIXTURE,"html.parser")
        a=malls.synchronize(conn,"2026-11-23T09:00:00",dt.date(2026,11,23),upsert,fetch)
        self.assertEqual(a["added"],a["found"])
        self.assertEqual(a["error"],"")
        b=malls.synchronize(conn,"2026-11-24T09:00:00",dt.date(2026,11,24),upsert,fetch)
        self.assertEqual(b["added"],0)
        self.assertEqual(b["changed"],0)
        def fail(_):raise PermissionError("robots disallows")
        c=malls.synchronize(conn,"2026-11-25T09:00:00",dt.date(2026,11,25),upsert,fail)
        self.assertIn("PermissionError",c["error"])
        self.assertTrue(saved)
        conn.close()


    def test_eci_market_is_only_a_single_current_dated_access_free_event(self):
        html = """<main><h1>Eventos en El Corte Inglés José Mesa y López</h1>
        <h1>Mercado Navideño Las Palmas</h1>
        <p>Ubicación: Avda. José Mesa y López, 18</p><p>Horario: 12:00 - 23:00</p>
        <p>Acceso: Libre</p>
        <p>Del 20 de noviembre de 2026 al 5 de enero de 2027 podrás recorrer las casetas.</p></main>"""
        soup=BeautifulSoup(html,"html.parser")
        row=malls.extract_eci_market(soup,dt.date(2026,11,23),2026)
        self.assertEqual(len(row),1)
        self.assertEqual(row[0]["free"],1)
        self.assertEqual(row[0]["price"],"Acceso libre")
        self.assertIn("Cierra el 25 de diciembre",row[0]["details"])
        self.assertEqual(malls.extract_eci_market(soup,dt.date(2027,1,6),2026),[])
        self.assertEqual(malls.extract_eci_market(soup,dt.date(2026,11,23),2025),[])
        without_free=html.replace("Acceso: Libre","Acceso: Por determinar")
        self.assertEqual(malls.extract_eci_market(without_free,dt.date(2026,11,23),2026),[])


if __name__=="__main__":
    unittest.main()
