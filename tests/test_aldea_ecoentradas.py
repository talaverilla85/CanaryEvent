"""Real municipal hall sessions, verified through an accessible original ticket outlet."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import aldea_ecoentradas as a
import sync_events as app

DATE=dt.date(2026,10,28)
VENUE='Centro Municipal de Cultura la Aldea'
LISTING="""<h1>Centro Municipal de Cultura la Aldea</h1>
<p>Gran Canaria - La Aldea de San Nicolás</p>
<a href="https://www.ecoentradas.com/elegirsesion/3405">Kike Pérez</a>
<a href="https://www.ecoentradas.com/elegirsesion/3405">Duplicado móvil</a>
<a href="https://malicious.example/elegirsesion/994">Falso</a>"""
SESSION="""<h1>Kike Pérez</h1><table><tr>
<td><span class="day">14</span><span class="month">Noviembre</span></td>
<td><span class="dates">20:00 | Centro Municipal de Cultura la Aldea</span></td>
<td><span class="price-sesion">10<small>€</small></span></td>
<td><a href="https://www.ecoentradas.com/elegirzona/3901">Seleccionar sesión</a></td>
</tr></table>"""
ZONE="""<h1>Kike Pérez</h1><div>En La Aldea de San Nicolás //
Centro Municipal de Cultura la Aldea // 14-11-26 // 20:00</div>"""

class EcoEntradasLaAldeaTests(unittest.TestCase):
    def test_current_evidence_parses_price_not_one_euro(self):
        links=a.session_links(BeautifulSoup(LISTING,"html.parser"))
        self.assertEqual(links,["https://www.ecoentradas.com/elegirsesion/3405"])
        title,rows=a.parse_sessions(BeautifulSoup(SESSION,"html.parser"))
        self.assertEqual(title,"Kike Pérez")
        self.assertEqual(rows[0]["price"],"10")
        self.assertEqual(a.verified_zone(BeautifulSoup(ZONE,"html.parser"),title,rows[0]),
                         dt.date(2026,11,14))

    def test_title_month_time_venue_year_must_agree_across_pages(self):
        title,rows=a.parse_sessions(BeautifulSoup(SESSION,"html.parser"))
        item=rows[0]
        for sample in (

            ZONE.replace("14-11-26","15-11-26"),
            ZONE.replace("20:00","21:00"),
            ZONE.replace("Centro Municipal de Cultura la Aldea","Otro Teatro"),
            ZONE.replace("Kike Pérez","Otra función"),
        ):
            self.assertIsNone(a.verified_zone(BeautifulSoup(sample,"html.parser"),title,item))
        self.assertEqual(a.verified_zone(BeautifulSoup(ZONE.replace("14-11-26","14-11-25"),"html.parser"),title,item),dt.date(2025,11,14))
        self.assertFalse(a.valid_page("https://www.ecoentradas.com.evil.invalid/elegirzona/3901","elegirzona"))
        self.assertFalse(a.valid_page("http://www.ecoentradas.com/elegirzona/3901","elegirzona"))
        self.assertFalse(a.valid_page("https://www.ecoentradas.com/elegirzona/3901?ticket=1","elegirzona"))

    def test_end_to_end_bounded_with_mocked_verified_pages(self):
        mapping={a.LISTING:LISTING,
                 "https://www.ecoentradas.com/elegirsesion/3405":SESSION,
                 "https://www.ecoentradas.com/elegirzona/3901":ZONE}
        class Resp:
            status_code=200
            headers={"content-type":"text/html"}
            def __init__(self,html):
                self.content=html.encode("utf8")
                self.text=html
        class Fake:
            def get(self,url,**kw):
                if url.endswith("/robots.txt"):
                    return Resp("User-agent: *\nAllow: /")
                return Resp(mapping[url])
        events,report=a.extract(Fake(),DATE,app.category,app.PLACES)
        self.assertEqual(report["found"],1)
        self.assertEqual(report["error"],"")
        self.assertEqual(len(events),1)
        e=events[0]
        self.assertEqual(e["municipality"],"La Aldea de San Nicolás")
        self.assertEqual(e["venue"],VENUE)
        self.assertEqual(e["start"],"2026-11-14T20:00:00")
        self.assertEqual(e["price"],"Desde 10 €")
        self.assertEqual(e["free"],0)
        self.assertEqual(e["category"],"cultura")
        self.assertEqual(e["source_url"],"https://www.ecoentradas.com/elegirsesion/3405")
        from verified_venue_coordinates import resolve
        lat,lng,precision=resolve(e["municipality"],e["venue"],app.PLACES)
        self.assertEqual(precision,"venue")
        self.assertAlmostEqual(lat,27.984758)
        self.assertAlmostEqual(lng,-15.780120)

    def test_other_region_or_ambiguous_source_rejected(self):
        with self.assertRaises(ValueError):
            a.session_links(BeautifulSoup(LISTING.replace("Gran Canaria","Tenerife"),"html.parser"))
        with self.assertRaises(ValueError):
            a.session_links(BeautifulSoup(LISTING.replace(VENUE,"Recinto Falso"),"html.parser"))

    def test_future_islands_recorded_as_candidates_but_not_published(self):
        import json
        x=json.loads((ROOT/"data/island_source_registry.json").read_text(encoding="utf8"))
        eco=next(s for s in x["source_profiles"] if s["id"]=="ecoentradas-interinsular")
        self.assertEqual(eco["islands"],["Gran Canaria"])
        self.assertIn("Fuerteventura",eco["potential_islands_to_validate"])
        self.assertEqual(x["active_publication_islands"],["Gran Canaria"])
        self.assertEqual(eco["adapter"],"aldea_ecoentradas")

    def test_no_publish_year_guessed_from_month_alone(self):
        title,rows=a.parse_sessions(BeautifulSoup(SESSION,"html.parser"))
        self.assertTrue(rows)
        self.assertIsNone(a.verified_zone(BeautifulSoup(
            ZONE.replace("14-11-26","14 noviembre"),"html.parser"),title,rows[0]))

if __name__=="__main__":
    unittest.main()
