import datetime as dt
import pathlib
import sys
import unittest
from bs4 import BeautifulSoup
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
import municipal_live_discovery as connector

class MunicipalLiveDiscoveryTests(unittest.TestCase):
    def test_four_municipalities_registered(self):
        self.assertEqual(set(connector.SITES),{"Firgas","Santa María de Guía","Agaete","Vega de San Mateo"})

    def test_discover_card_behind_read_more(self):
        html='<article><h3>Concierto de otoño en Agaete</h3><a href="/noticias/concierto-de-otono">Leer más</a></article>'
        self.assertEqual(len(connector.discover(BeautifulSoup(html,"html.parser"),"agaete.es")),1)

    def test_guia_recovers_real_headline_not_metadata_excerpt(self):
        html='''<div class="x-recent-posts">
          <a href="https://santamariadeguia.es/guia-celebra-este-sabado-la-v-noche-de-finaos/">
          <article><span class="post-categories">Noticias,Cultura | 04/11/2026</span>
          <h3 class="h-recent-posts">Guía celebra este sábado la V Noche de Finaos</h3>
          <span>Un extracto que no debe formar parte del título</span></article></a>
          <a href="https://santamariadeguia.es/guia-pone-en-marcha-proyecto-digital/">
          <article><h3 class="h-recent-posts">Guía pone en marcha un proyecto escolar</h3></article></a>
          </div>'''
        links=connector.discover(BeautifulSoup(html,"html.parser"),"santamariadeguia.es")
        self.assertEqual(len(links),1)
        self.assertEqual(links[0][1],"Guía celebra este sábado la V Noche de Finaos")
        self.assertNotIn("Noticias",links[0][1])

    def test_guia_publishes_only_correlated_time_date_and_venue(self):
        url="https://santamariadeguia.es/guia-celebra-este-sabado-la-v-noche-de-finaos/"
        html='''<article>
          <time datetime="2026-11-04T12:24:51+00:00">4/11/2026</time>
          <div class="entry-content">El encuentro se celebrará en la Iglesia de Santa María de Guía,
          a las 20:00 horas. Guía celebrará este sábado 7 de noviembre
          la quinta edición de la Noche de Finaos.</div></article>'''
        row=connector.parse_article(BeautifulSoup(html,"html.parser"),
             "Guía celebra este sábado la V Noche de Finaos",url,
             "Santa María de Guía",dt.date(2026,11,7),lambda x:"cultura")
        self.assertIsNotNone(row)
        self.assertEqual(row["title"],"Guía celebra este sábado la V Noche de Finaos")
        self.assertEqual(row["start"],"2026-11-07T20:00:00")
        self.assertEqual(row["venue"],"Iglesia de Santa María de Guía")
        self.assertEqual(row["source_url"],url)

    def test_guia_race_uses_start_time_not_early_registration(self):
        html='''<article>
        <time datetime="2026-11-05T12:40:26+00:00"></time>
        <div class="entry-content">La prueba se celebrará el sábado 21 de noviembre.
        La plaza de San Pedro de La Atalaya ha sido escogida como punto de encuentro y de salida.
        La prueba dará comienzo a las 11:00 horas.
        La entrega de dorsales será a las 9:00 horas y el calentamiento a partir de las 10:30 horas.
        </div></article>'''
        row=connector.parse_article(BeautifulSoup(html,"html.parser"),
            "Guía volverá a correr contra la violencia de género el próximo 21 de noviembre",
            "https://santamariadeguia.es/guia-volvera-a-correr-contra-la-violencia-de-genero/",
            "Santa María de Guía",dt.date(2026,11,7),lambda x:"deporte")
        self.assertIsNotNone(row)
        self.assertEqual(row["start"],"2026-11-21T11:00:00")
        self.assertEqual(row["venue"],"Plaza de San Pedro de La Atalaya")

    def test_guia_rejects_multiday_ambiguous_or_missing_evidence(self):
        base='''<article><time datetime="2026-11-06T12:00:00+00:00"></time>
          <div class="entry-content">{}</div></article>'''
        title="El Circus Frances ofrece espectáculo familiar en Guía"
        samples=[
            "El circo se celebrará del 6 al 11 de noviembre, a las 18:30 horas en el Parque de la Atalaya.",
            "El circo se celebrará el 7 de noviembre y el 9 de noviembre, a las 18:30 horas en el Parque de la Atalaya.",
            "El circo se celebrará el 7 de noviembre, a las 18:30 horas en varios recintos.",
            "El circo se celebrará el 7 de noviembre, en la Plaza de La Atalaya.",
            "El circo se celebrará el 7 de noviembre, a las 18:30 horas sin recinto indicado.",
        ]
        for body in samples:
            with self.subTest(body=body):
                self.assertIsNone(connector.parse_article(
                    BeautifulSoup(base.format(body),"html.parser"),title,
                    "https://santamariadeguia.es/circus-frances-en-guia/",
                    "Santa María de Guía",dt.date(2026,11,7),lambda x:"familia"))

    def test_quarantine_wrongly_dated_old_guia_news_card(self):
        old={"source_name":"Municipio · descubrimiento oficial · Santa María de Guía",
             "title":"Noticias,Cultura | 03/11/2026 Guía reúne a seis agrupaciones en el IX Festival Internacional de Música Coral",
             "start":"2026-11-28"}
        self.assertTrue(connector.invalid_legacy_guia(old))
        good=dict(old,title="Guía celebra este sábado la V Noche de Finaos")
        self.assertFalse(connector.invalid_legacy_guia(good))
        unrelated=dict(old,source_name="Ayuntamiento de Telde · noticias oficiales")
        self.assertFalse(connector.invalid_legacy_guia(unrelated))

    def test_guia_does_not_guess_year_from_crawl_time(self):
        html='''<article><div class="entry-content">
        La Noche de Finaos se celebrará el 7 de noviembre, a las 20:00
        en la Iglesia de Santa María de Guía.</div></article>'''
        self.assertIsNone(connector.parse_article(
            BeautifulSoup(html,"html.parser"),"La Noche de Finaos",
            "https://santamariadeguia.es/noche-de-finaos/",
            "Santa María de Guía",dt.date(2026,11,7),lambda x:"cultura"))

    def test_reject_signup_deadline(self):
        soup=BeautifulSoup('<article><p>Inscripción hasta el 2 de noviembre de 2026 en el Centro Cultural.</p></article>',"html.parser")
        self.assertIsNone(connector.parse_article(soup,"Plazo de inscripción para taller", "https://agaete.es/noticias/a","Agaete",dt.date(2026,10,29),lambda x:"cultura"))

    def test_reject_ambiguous_dates(self):
        soup=BeautifulSoup('<article>Concierto el 2 de noviembre de 2026 y el 3 de noviembre de 2026 en la Casa de la Cultura</article>',"html.parser")
        self.assertIsNone(connector.parse_article(soup,"Concierto de otoño","https://agaete.es/noticias/concierto","Agaete",dt.date(2026,10,29),lambda x:"cultura"))

    def test_reject_old_year(self):
        soup=BeautifulSoup('<article>Concierto el 2 de noviembre de 2025 en la Casa de la Cultura</article>',"html.parser")
        self.assertIsNone(connector.parse_article(soup,"Concierto de otoño","https://agaete.es/noticias/concierto","Agaete",dt.date(2026,10,29),lambda x:"cultura"))

if __name__=="__main__":unittest.main()
