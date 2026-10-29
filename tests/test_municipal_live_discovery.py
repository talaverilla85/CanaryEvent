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
