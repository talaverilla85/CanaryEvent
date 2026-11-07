"""La Aldea events must come only from robots-permitted public EcoEntradas pages."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import aldea_ecoentradas as a
import sync_events as sync

TODAY=dt.date(2026,11,7)
LINK="https://ecoentradas.com/eventos/kike-perez-2026-11-14"
POSTER="https://ecoentradas.com/cartel/SkxC6nzG/treatedEE7X90f8.jpg"
LISTING="""<h1>Centro Municipal de Cultura la Aldea</h1>
<p>Gran Canaria - La Aldea de San Nicolás</p>
<a href="https://ecoentradas.com/eventos/kike-perez-2026-11-14">Kike Pérez</a>
<a href="https://ecoentradas.com/eventos/kike-perez-2026-11-14">Duplicado móvil</a>
<a href="https://www.ecoentradas.com/eventos/kike-perez-2026-11-14">Enlace antiguo</a>
<a href="https://ecoentradas.com/elegirzona/3901">Zona prohibida por robots</a>
<a href="https://malicious.example/eventos/obra-2026-11-14">Falso</a>"""
EVENT={
    "@type":"Event",
    "@id":LINK,
    "name":"Kike Pérez · 14/11/2026 20:00",
    "startDate":"2026-11-14T20:00:00+00:00",
    "endDate":"2026-11-14T21:30:00+00:00",
    "eventStatus":"https://schema.org/EventScheduled",
    "url":LINK,
    "image":POSTER,
    "location":{
        "@type":"Place",
        "name":"Centro Municipal de Cultura la Aldea",
        "address":{
            "@type":"PostalAddress",
            "streetAddress":"C. Gral. Franco, 30, 35470 La Aldea de San Nicolas de Tolentino",
            "addressLocality":"Gran Canaria",
            "addressCountry":"ES",
        },
        "url":a.LISTING,
    },
    "offers":{
        "@type":"Offer",
        "url":"https://ecoentradas.com/elegirzona/3901",
        "price":"10.00",
        "priceCurrency":"EUR",
    },
}
def page(event=None,title="Kike Pérez"):
    data=EVENT if event is None else event
    return BeautifulSoup(
        '<h1>'+title+'</h1><script type="application/ld+json">'+
        json.dumps(data,ensure_ascii=False)+'</script>',"html.parser")


class EcoEntradasLaAldeaTests(unittest.TestCase):
    def test_canonical_hall_and_only_public_links(self):
        self.assertEqual(a.ROOT,"https://ecoentradas.com")
        self.assertEqual(a.LISTING,
                         "https://ecoentradas.com/recintos/centro-municipal-de-cultura-la-aldea")
        links=a.public_links(BeautifulSoup(LISTING,"html.parser"))
        self.assertEqual(links,[LINK])
        self.assertTrue(a.public_url(LINK))
        self.assertFalse(a.public_url("https://www.ecoentradas.com/eventos/kike-perez-2026-11-14"))
        self.assertFalse(a.public_url("https://ecoentradas.com/elegirzona/3901"))
        self.assertFalse(a.public_url(LINK+"?idioma=en"))
        self.assertFalse(a.public_url(LINK.replace(".com",".com.evil.example")))

    def test_real_venue_schema_fields_are_required(self):
        record=a.event_record(page(),LINK,TODAY,sync.category)
        self.assertIsNotNone(record)
        self.assertEqual(record["title"],"Kike Pérez")
        self.assertEqual(record["start"],"2026-11-14T20:00:00")
        self.assertEqual(record["venue"],a.VENUE)
        self.assertEqual(record["municipality"],"La Aldea de San Nicolás")
        self.assertEqual(record["source_url"],LINK)
        self.assertEqual(record["price"],"Desde 10 €")
        self.assertEqual(record["free"],0)
        self.assertEqual(record["category"],"cultura")
        self.assertEqual(record["image_url"],POSTER)
        self.assertEqual(record["image_status"],"official_remote")
        from verified_venue_coordinates import resolve
        lat,lng,precision=resolve(record["municipality"],record["venue"],sync.PLACES)
        self.assertEqual(precision,"venue")
        self.assertAlmostEqual(lat,27.984758)
        self.assertAlmostEqual(lng,-15.780120)

    def test_schema_date_venue_identity_and_status_must_agree(self):
        changes=[
            {"startDate":"2026-11-15T20:00:00+00:00"},
            {"startDate":"2026-11-14"},
            {"startDate":"2026-11-14T20:00:00"},
            {"startDate":"2025-11-14T20:00:00+00:00"},
            {"url":"https://ecoentradas.com/eventos/otro-show-2026-11-14"},
            {"eventStatus":"https://schema.org/EventCancelled"},
            {"name":"Una función diferente"},
            {"location":{**EVENT["location"],"name":"Otro teatro"}},
            {"location":{**EVENT["location"],
                         "address":{**EVENT["location"]["address"],"addressLocality":"Tenerife"}}},
            {"location":{**EVENT["location"],"url":"https://ecoentradas.com/recintos/otro-recinto"}},
            {"offers":{**EVENT["offers"],"price":"Gratis"}},
            {"offers":{**EVENT["offers"],"price":"10.00","priceCurrency":"USD"}},
            {"offers":{**EVENT["offers"],"price":"6000"}},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNone(a.event_record(page({**EVENT,**change}),LINK,TODAY,sync.category))
        self.assertIsNone(a.event_record(page(),LINK,dt.date(2026,11,15),sync.category))

    def test_no_image_stolen_from_another_host(self):
        row=a.event_record(page({**EVENT,"image":"https://example.org/poster.png"}),
                           LINK,TODAY,sync.category)
        self.assertIsNotNone(row)
        self.assertEqual(row["image_url"],"")
        self.assertEqual(row["image_status"],"not_available")

    def test_end_to_end_fetches_no_seat_map_or_checkout(self):
        class Response:
            status_code=200
            headers={"content-type":"text/html"}
            def __init__(self,html):
                self.content=html.encode("utf8")
                self.text=html
        mapping={a.LISTING:LISTING,
                 LINK:str(page())}
        class Fake:
            def __init__(self):
                self.requested=[]
            def get(self,url,**kw):
                self.requested.append(url)
                if url.endswith("/robots.txt"):
                    return Response("User-agent: *\nDisallow: /elegirzona/\nDisallow: /checkout/\n")
                return Response(mapping[url])
        fake=Fake()
        rows,report=a.extract(fake,TODAY,sync.category,sync.PLACES)
        self.assertEqual(report["found"],1)
        self.assertEqual(report["sessions_verified"],1)
        self.assertEqual(report["error"],"")
        self.assertEqual(len(rows),1)
        self.assertEqual(fake.requested,[a.ROOT+"/robots.txt",a.LISTING,LINK])
        self.assertFalse(any("/elegirzona/" in url for url in fake.requested))

    def test_explicit_robot_disallow_prevents_event_fetch(self):
        class Response:
            status_code=200
            headers={"content-type":"text/html"}
            def __init__(self,text):
                self.text=text
                self.content=text.encode()
        class Fake:
            def __init__(self):
                self.calls=[]
            def get(self,url,**kw):
                self.calls.append(url)
                if url.endswith("robots.txt"):
                    return Response("User-agent: *\nDisallow: /eventos/\n")
                return Response(LISTING)
        fake=Fake()
        rows,report=a.extract(fake,TODAY,sync.category,sync.PLACES)
        self.assertEqual(rows,[])
        self.assertIn("PermissionError",report["error"])
        self.assertEqual(fake.calls,[a.ROOT+"/robots.txt",a.LISTING])

    def test_robots_unavailable_fails_closed(self):
        class Fake:
            def get(self,url,**kw):
                class Response:
                    status_code=403
                return Response()
        with self.assertRaisesRegex(RuntimeError,"robots unavailable"):
            a.extract(Fake(),TODAY,sync.category,sync.PLACES)

    def test_other_town_listing_rejected(self):
        wrong=LISTING.replace("Gran Canaria","Tenerife")
        with self.assertRaises(ValueError):
            a.public_links(BeautifulSoup(wrong,"html.parser"))
        wrong=LISTING.replace("Centro Municipal de Cultura la Aldea","Recinto desconocido")
        with self.assertRaises(ValueError):
            a.public_links(BeautifulSoup(wrong,"html.parser"))

    def test_future_islands_registered_as_candidates_but_not_published(self):
        registry=json.loads((ROOT/"data/island_source_registry.json").read_text(encoding="utf8"))
        eco=next(s for s in registry["source_profiles"] if s["id"]=="ecoentradas-interinsular")
        self.assertEqual(eco["islands"],["Gran Canaria"])
        self.assertIn("Fuerteventura",eco["potential_islands_to_validate"])
        self.assertEqual(registry["active_publication_islands"],["Gran Canaria"])
        self.assertEqual(eco["adapter"],"aldea_ecoentradas")


if __name__=="__main__":
    unittest.main()
