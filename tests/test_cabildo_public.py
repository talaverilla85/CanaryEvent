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
    def test_fresh_scans_report_normal_idle_cycle(self):
        import sqlite3
        from unittest.mock import patch
        now="2026-10-27T10:00:00+00:00"
        day=dt.date(2026,10,27)
        urls=[f"https://www.eventosgrancanaria.com/event/E-20261027-{i:04d}/evento" for i in range(25)]
        with sqlite3.connect(":memory:") as conn:
            conn.execute("""CREATE TABLE cabildo_scans(
                url TEXT PRIMARY KEY,checked_at TEXT NOT NULL,outcome TEXT NOT NULL,
                image_inspected INTEGER NOT NULL,facts_inspected INTEGER NOT NULL)""")
            conn.executemany("INSERT INTO cabildo_scans VALUES(?,?,?,1,1)",
                             [(url,now,"valid") for url in urls])
            with patch.object(cabildo,"scan_allowed"),patch.object(cabildo,"list_public_events",return_value=[(u,day) for u in urls]):
                report=cabildo.synchronize(conn,now,day,app.PLACES,app.norm,app.category,
                                           lambda c,e:"unchanged")
        self.assertEqual(report["eligible_urls"],25)
        self.assertEqual(report["skipped_recent"],25)
        self.assertEqual(report["due_urls"],0)
        self.assertEqual(report["scanned"],0)
        self.assertEqual(report["queued_remaining"],0)
        self.assertEqual(report["error"],"")

if __name__=="__main__":unittest.main()
