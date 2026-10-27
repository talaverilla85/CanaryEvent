"""Named venues must be grounded in specific, unambiguous organizer text."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import venue_facts as v
import source_facts as source
import sync_events as app
import arucas_agenda as arucas
import tejeda_agenda as tejeda

class VenueTests(unittest.TestCase):
    def test_labelled_venue(self):
        self.assertEqual(v.from_description(
            "Lugar: Biblioteca Municipal Saulo Torón Información en la Biblioteca Municipal Saulo Torón o llamando al 928","Telde"),
            "Biblioteca Municipal Saulo Torón")
    def test_glued_labels(self):
        self.assertEqual(v.from_description(
            "Duración: 9 mesesPrecio: 45€ / mesLugar: Casa de la Juventud de Telde Elige el horario:Grupo 1","Telde"),
            "Casa de la Juventud de Telde")
    def test_named_building(self):
        self.assertEqual(v.from_description(
            "La exposición de la artista en el Centro de Arte La Regenta. Entrada libre.","Las Palmas de Gran Canaria"),
            "Centro de Arte La Regenta")
    def test_quoted_building(self):
        self.assertEqual(v.from_description(
            "El viernes se abre al público en la “Casa Gourié-Museo municipal de Arucas, dirigida por Cultura, la exposición.","Arucas"),
            "Casa Gourié-Museo municipal de Arucas")
    def test_lower_floor(self):
        self.assertEqual(v.from_description(
            "Todos los jueves en la planta baja de la Biblioteca Municipal de Tejeda. Dos grupos.","Tejeda"),
            "Biblioteca Municipal de Tejeda")
    def test_nfkc(self):
        self.assertEqual(v.from_description(
            "El cine vuelve a ser protagonista en el 𝗖𝗲𝗻𝘁𝗿𝗼 𝗖𝘂𝗹𝘁𝘂𝗿𝗮𝗹 𝗠𝗮𝘀𝗽𝗮𝗹𝗼𝗺𝗮𝘀 con una programación.","San Bartolomé de Tirajana"),
            "Centro Cultural Maspalomas")
    def test_truncated_location_rejected(self):
        self.assertEqual(v.from_description("Viernes. 📍 Biblioteca M","Mogán"),"")
    def test_not_a_venue(self):
        for desc in ("Se celebra en Telde. Organiza el Ayuntamiento de Telde.",
                     "Las Bibliotecas Municipales de Mogán te invitan al taller.",
                     "Visita a las Salinas del Bufadero, en Bañaderos.",
                     "📍 Telde"):
            with self.subTest(desc=desc):
                self.assertEqual(v.from_description(desc,"Telde"),"")
    def test_ambiguous_multi_venue(self):
        for desc in ("Primero en la Plaza de San Rafael, después en el Recinto Ferial de Vecindario.",
                     "El programa tiene varias sedes y una actividad en el Teatro Municipal.",
                     "Talleres en cuatro formatos: 3 talleres, 4 sesiones. Los talleres se desarrollarán en el Espacio Violeta."):
            with self.subTest(desc=desc):
                self.assertEqual(v.from_description(desc,"Las Palmas de Gran Canaria"),"")
    def test_cabildo_municipal_structured_place_fallback(self):
        doc='''<script type="application/ld+json">{"@type":"Event",
                 "location":{"@type":"Place","name":"Telde"},
                 "description":"Lugar: Biblioteca Municipal Saulo Torón"}</script>'''
        soup=BeautifulSoup(doc,"html.parser")
        self.assertEqual(source.verified_venue(soup,source.event_schema(soup),"Telde",app.norm),
                         "Biblioteca Municipal Saulo Torón")
    def test_arucas_official_detail(self):
        class Response:
            def __init__(self,status,content=b""):
                self.status_code=status
                self.content=content
        class Client:
            def __init__(self):self.urls=[]
            def get(self,url,**kwargs):
                self.urls.append(url)
                if url.endswith("robots.txt"):return Response(404)
                return Response(200,b'<div class="entry-content">Exposicion en la Casa Gourie-Museo municipal de Arucas, este viernes.</div>')
        c=Client()
        item={"venue":"Consultar el recinto en la ficha oficial",
              "source_url":"https://www.arucas.org/modules.php?mod=portal&file=ver_gen&id=ABC="}
        with patch("time.sleep"):
            arucas.enrich_venues([item],client=c)
        self.assertEqual(item["venue"],"Casa Gourie-Museo municipal de Arucas")
        self.assertEqual(len(c.urls),2)
    def test_tejeda_article(self):
        doc='''<meta property="article:published_time" content="2026-10-26T10:00:00+00:00">
          <div class="entry-content">Empezamos el 5 de noviembre de 2026.
          Todos los jueves en la planta baja de la Biblioteca Municipal de Tejeda.</div>'''
        e=tejeda.parse_article(BeautifulSoup(doc,"html.parser"),"Clases de yoga",
                               "https://tejeda.eu/clases-de-yoga-otono-2026/",
                               dt.date(2026,10,27),app.category)
        self.assertIsNotNone(e)
        self.assertEqual(e["venue"],"Biblioteca Municipal de Tejeda")
if __name__=="__main__":unittest.main()
