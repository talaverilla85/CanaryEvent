"""Venue evidence, restricted organizer-fetch and publication quality contracts."""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import organizer_venues as org
import venue_quality as quality
import sync_events as sync

def soup(title,body,schema=""):
    return BeautifulSoup(f'<html><head><title>{title}</title></head><body><article>'
        f'<h1>{title}</h1>{body}</article>{schema}</body></html>',"html.parser")

class OrganizerVenueTests(unittest.TestCase):
    def test_official_labelled_venues_without_colon(self):
        cases=[
            ("La voz de los libros","Localización Biblioteca Dolores Campos-Herrero c/ Zaragoza, s/n Other Events",
             "Biblioteca Dolores Campos-Herrero"),
            ("Bodas de sangre","Precio Gratuito Lugar Biblioteca Municipal Josefina de La Torre Servicios: préstamo",
             "Biblioteca Municipal Josefina de La Torre"),
            ("Efecto cinema","Cine Lugar Yelmo cine Las Arenas Fecha Fechas del evento Mié. 28",
             "Yelmo cine Las Arenas"),
            ("HIJOS DE LA BRUMA","HIJOS DE LA BRUMA Lugar La Grada Fecha Fechas del evento",
             "La Grada"),
            ("Taller de Narración Oral","Lugar: Biblioteca Municipal Saulo Torón Información en la biblioteca",
             "Biblioteca Municipal Saulo Torón"),
        ]
        for title,body,expected in cases:
            with self.subTest(title=title):
                self.assertEqual(org.parse_official(soup(title,body),title,"Las Palmas de Gran Canaria"),expected)
    def test_schema_location_same_event(self):
        sc='<script type="application/ld+json">{"@type":"Event","name":"Concierto","location":{"name":"Teatro Guiniguada"}}</script>'
        self.assertEqual(org.parse_official(soup("Concierto","Programa de música.",sc),"Concierto","Las Palmas de Gran Canaria"),"Teatro Guiniguada")
    def test_schema_for_other_event_rejected(self):
        sc='<script type="application/ld+json">{"@type":"Event","name":"Otro evento","location":{"name":"Auditorio Alfredo Kraus"}}</script>'
        self.assertEqual(org.parse_official(soup("Concierto","Programa de música.",sc),"Concierto","Las Palmas de Gran Canaria"),"")
    def test_must_match_page_title(self):
        self.assertEqual(org.parse_official(soup("Fiestas de barrio","Lugar: Plaza de San Juan"),"Concierto","Telde"),"")
    def test_itinerant_event_no_single_point(self):
        self.assertEqual(org.parse_official(soup("Clásicos en Vegueta","Es un recorrido itinerante. Lugar Barrio de Vegueta"),"Clásicos en Vegueta","Las Palmas de Gran Canaria"),"")
    def test_generic_municipality_not_venue(self):
        self.assertFalse(quality.named_venue({"venue":"Telde","municipality":"Telde"}))
        self.assertFalse(quality.named_venue({"venue":"CENTRO CULTURAL","municipality":"Arucas"}))
        self.assertTrue(quality.named_venue({"venue":"La Grada","municipality":"Las Palmas de Gran Canaria"}))
    def test_host_exact_allowlist(self):
        for u in ("http://teldecultura.org/events/test","https://evil-teldecultura.org/events/test",
                  "https://teldecultura.org.evil.com/events/test",
                  "https://user:pass@teldecultura.org/events/test",
                  "https://127.0.0.1/events/test","https://teldecultura.org/"):
            self.assertEqual(org.valid_url(u),"",u)
        self.assertEqual(org.valid_url("https://teldecultura.org/events/concierto/"),
                         "https://teldecultura.org/events/concierto/")
    def test_publication_gate_retains_unverified_for_review(self):
        items=[{"id":1,"title":"A","municipality":"Telde","venue":"Biblioteca Municipal Saulo Torón"},
               {"id":2,"title":"B","municipality":"Telde","venue":"Consultar el recinto en la ficha oficial"},
               {"id":3,"title":"C","municipality":"Telde","venue":"Telde"}]
        good,bad=quality.split_verified(items)
        self.assertEqual([x["id"] for x in good],[1])
        self.assertEqual([x["id"] for x in bad],[2,3])

    def test_secondary_enrichment_and_refresh_preservation(self):
        date=sync.TODAY+dt.timedelta(days=2)
        title="Taller de cómic y cuentos ilustrados"
        url="https://teldecultura.org/events/taller-de-comic-y-cuentos-ilustrados/"
        data={"title":title,"start":date.isoformat(),"end":None,"municipality":"Telde",
              "venue":"Consultar el recinto en la ficha oficial","category":"familia",
              "free":None,"price":"","details":"","source_name":"Portal oficial de Eventos Gran Canaria (Cabildo)",
              "source_url":"https://www.eventosgrancanaria.com/event/E-20261029-0000/taller",
              "organizer_url":url,"status":"approved"}
        class Response:
            def __init__(self,code,content=b""):
                self.status_code=code;self.content=content
                self.text=content.decode("utf-8",errors="ignore")
                self.headers={"content-type":"text/html"}
        class Client:
            def __init__(self):self.urls=[]
            def get(self,url,**kwargs):
                self.urls.append(url)
                if url.endswith("/robots.txt"):return Response(404)
                return Response(200,soup(title,"Lugar: Biblioteca Municipal Saulo Torón").encode("utf-8"))
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory=sqlite3.Row
            sync.init(conn)
            sync.upsert(conn,data)
            c=Client()
            stats=org.enrich(conn,sync.NOW,sync.TODAY,client=c,max_pages=2,sleep=lambda n:None)
            self.assertEqual(stats["changed"],1)
            self.assertEqual(conn.execute("SELECT venue FROM events").fetchone()[0],
                             "Biblioteca Municipal Saulo Torón")
            self.assertEqual(len(c.urls),2)
            self.assertEqual(sync.upsert(conn,data),"unchanged")
            self.assertEqual(conn.execute("SELECT venue FROM events").fetchone()[0],
                             "Biblioteca Municipal Saulo Torón")
class SameHostRedirectTests(unittest.TestCase):
    def test_redirect_to_new_path_on_same_official_domain(self):
        old="https://www.casafrica.es/es/evento/concierto-antiguo"
        new="https://www.casafrica.es/es/evento/conciertos-nuevo"
        class Response:
            def __init__(self,code,location=""):
                self.status_code=code
                self.headers={"Location":location,"content-type":"text/html"}
        class Client:
            def __init__(self):self.calls=[]
            def get(self,url,**kwargs):
                self.calls.append(url)
                if url.endswith("/robots.txt"):return Response(404)
                if url==new:return Response(200)
                raise ValueError("Unexpected URL "+url)
        client=Client()
        result=org._same_official_redirect(client,old,Response(301,"/es/evento/conciertos-nuevo"),{})
        self.assertEqual(result.status_code,200)
        self.assertEqual(client.calls,["https://www.casafrica.es/robots.txt",new])
    def test_external_redirect_forbidden(self):
        old="https://www.casafrica.es/es/evento/concierto-antiguo"
        class Response:
            status_code=301
            headers={"Location":"https://teldecultura.org/events/otro"}
        class Client:
            def get(self,*a,**k):
                raise AssertionError("Never contact the external host")
        with self.assertRaises(PermissionError):
            org._same_official_redirect(Client(),old,Response(),{})
    def test_http_redirect_forbidden(self):
        old="https://www.casafrica.es/es/evento/concierto-antiguo"
        class Response:
            status_code=301
            headers={"Location":"http://www.casafrica.es/es/evento/a"}
        with self.assertRaises(PermissionError):
            org._same_official_redirect(None,old,Response(),{})

if __name__=="__main__":unittest.main()
