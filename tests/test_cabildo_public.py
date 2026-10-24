import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import cabildo_public as cabildo
import sync_events as app

def page(title,municipio,date_label,time_label,venue="Teatro Municipal",status="EventScheduled"):
    return f'''<!doctype html><html><main>
      <h1 class="event-detail__title">{title}</h1>
      <div class="event-detail__details-list">
        <p class="event-detail__text">{venue}</p>
        <p class="event-detail__text">{municipio}</p>
        <p class="event-detail__text">{date_label}</p>
        <p class="event-detail__text">{time_label}</p>
      </div>
      <script type="application/ld+json">{{"@type":"Event","eventStatus":"https://schema.org/{status}"}}</script>
    </main></html>'''

class OfficialCatalogTests(unittest.TestCase):
    def test_exact_date_with_hour(self):
        day=app.TODAY+dt.timedelta(days=2)
        e=cabildo.extract_factual_event(page("Concierto Popular","Ingenio",day.strftime("%d/%m/%Y"),"20:30 - 22:00"),
           "https://www.eventosgrancanaria.com/event/E-20261024-0001/ejemplo",app.TODAY,app.PLACES,app.norm,app.category)
        self.assertEqual(e["start"],day.isoformat()+"T20:30:00")
        self.assertEqual(e["end"],day.isoformat()+"T22:00:00")
        self.assertEqual(e["municipality"],"Ingenio")
    def test_date_only_not_midnight(self):
        day=app.TODAY+dt.timedelta(days=5)
        e=cabildo.extract_factual_event(page("Mercado Artesano","Arucas",day.strftime("%d/%m/%Y"),"00:00 - 00:00"),
           "https://www.eventosgrancanaria.com/event/E-20261024-0002/ejemplo",app.TODAY,app.PLACES,app.norm,app.category)
        self.assertEqual(e["start"],day.isoformat())
        self.assertIsNone(e["end"])
    def test_event_period_is_not_fake_sessions(self):
        a=app.TODAY-dt.timedelta(days=8)
        b=app.TODAY+dt.timedelta(days=10)
        dates=a.strftime("%d/%m/%Y")+" - "+b.strftime("%d/%m/%Y")
        e=cabildo.extract_factual_event(page("Exposición de Arte","Telde",dates,"00:00 - 00:00"),
           "https://www.eventosgrancanaria.com/event/E-20261024-0003/ejemplo",app.TODAY,app.PLACES,app.norm,app.category)
        self.assertEqual(e["start"],a.isoformat())
        self.assertEqual(e["end"],b.isoformat())
        self.assertIn("Periodo",e["details"])
    def test_no_municipality_skips_page(self):
        day=app.TODAY+dt.timedelta(days=1)
        e=cabildo.extract_factual_event(page("Algo Cultural","Inventado",day.strftime("%d/%m/%Y"),"18:00 - 19:00"),
           "https://www.eventosgrancanaria.com/event/E-20261024-0004/ejemplo",app.TODAY,app.PLACES,app.norm,app.category)
        self.assertIsNone(e)
if __name__=="__main__":unittest.main()
