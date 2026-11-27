"""Regression coverage for event descriptions, official excursion facts and pages."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import event_copy_quality as quality
import santabrigida_agenda as santa

TRIP_DETAILS = """<p>El Club Municipal de Mayores organiza para el próximo viernes
27 de noviembre una salida cultural para visitar el Jardín de la Marquesa de
Arucas. El Jardín de la ... <a title="Salida cultural" class="read-more"
href="https://eventos.santabrigida.es/eventos/salida-cultural-jardin-de-la-marquesa/"
aria-label="Leer más sobre salida cultural">Leer más</a></p>\\n"""


class CopyQualityTests(unittest.TestCase):
    def test_strips_source_html_anchors_newline_entities_and_teasers(self):
        clean=quality.plain_description(TRIP_DETAILS)
        self.assertIn("El Club Municipal de Mayores",clean)
        self.assertIn("Consulta la publicación original",clean)
        for tag in ("<p>","<a","href=","class=","\\n","Leer más"):
            self.assertNotIn(tag,clean)
        self.assertEqual(quality.plain_description("<p>Vive &amp; disfruta&nbsp;hoy</p>"),
                         "Vive & disfruta hoy")

    def test_precise_excursion_terms_only_for_actual_2026_event(self):
        row={
            "source_name":santa.NAME,
            "source_url":quality.TRIP_SOURCE,
            "start":"2026-11-27T09:00:00",
            "details":TRIP_DETAILS,
            "venue":"CLUB MUNICIPAL DE MAYORESDE LA VILLA DE SANTA BRIGIDA",
            "price":"","free":None,"accuracy":"municipality",
            "lat":28.035,"lng":-15.497
        }
        got=quality.normalize_event(row)
        self.assertEqual(got["venue"],"Club Municipal de Mayores de Santa Brígida")
        self.assertEqual(got["price"],"16 € almuerzo + 6 € entrada")
        self.assertEqual(got["free"],0)
        self.assertIn("solo puede participar si quedan plazas",got["details"])
        self.assertIn("punto exacto de encuentro",got["details"])
        self.assertIn("transporte y seguro gratuitos",got["details"])
        self.assertEqual(got["accuracy"],"municipality")
        self.assertEqual(got["lat"],28.035)
        old={**row,"start":"2027-11-27T09:00:00"}
        normalized=quality.normalize_event(old)
        self.assertEqual(normalized["price"],"")
        self.assertNotIn("16 €",normalized["details"])
        self.assertNotIn("href=",normalized["details"])
        self.assertEqual(row["details"],TRIP_DETAILS)

    def test_official_article_description_prefers_plain_text_and_booking_notes(self):
        soup=BeautifulSoup("""
        <section class="tribe-events-single-event-description">
         <p>La biblioteca prepara una nueva sesión de cuentos para familias.</p>
         <p>Se narrarán historias y habrá actividades para niños.</p>
         <p>La inscripción es obligatoria; reserva en biblioteca@santabrigida.es.</p>
         <p>Plazas limitadas por aforo.</p>
         <a class="read-more" href="https://example.com">Leer más</a>
        </section>""","html.parser")
        text=santa.article_description(soup)
        self.assertIn("biblioteca",text)
        self.assertIn("reserva en biblioteca@",text)
        self.assertIn("Plazas limitadas",text)
        self.assertNotIn("<p>",text)
        self.assertNotIn("Leer más",text)
        self.assertEqual(santa.article_description(BeautifulSoup("<p>no article</p>","html.parser")),"")

    def test_malformed_content_does_not_inject_html(self):
        text=quality.plain_description(
            '<p>Actividad pública</p><script>alert("x")</script>'
            '<a class="read-more" href="javascript:alert(1)">Leer más</a>')
        self.assertEqual(text,"Actividad pública. Consulta la publicación original para ampliar la información.")


if __name__=="__main__":
    unittest.main()
