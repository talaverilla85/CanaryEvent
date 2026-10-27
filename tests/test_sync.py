import datetime as dt
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_events as app

class SyncTests(unittest.TestCase):
    def test_ingenio_structured_listing(self):
        today=app.TODAY
        sample=f'''<article class="mec-event-article mec-toggle-{today:%Y%m}-919">
           <h3 class="mec-event-title"><a href="https://ingenio.es/events/ejemplo/">Concierto de prueba</a></h3>
           <span class="mec-start-date-label">{today.day} {list(app.MONTHS.keys())[list(app.MONTHS.values()).index(today.month)]}</span>
           <span class="mec-start-time">20:30</span><span class="mec-end-time">22:00</span>
           <div class="mec-venue-details"><span>Teatro Municipal</span></div>
           </article>'''
        events=app.extract_ingenio(BeautifulSoup(sample,"html.parser"))
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["start"][:10],today.isoformat())
        self.assertEqual(events[0]["category"],"musica")

    def test_aguimes_free_venue_and_url(self):
        day=app.TODAY+dt.timedelta(days=3)
        month=[k for k,v in app.MONTHS.items() if v==day.month and len(k)==3][0]
        sample=f'''<div class="event"><div class="name"><a href="https://eventos.aguimes.es/events/test">
        Cine de Terror</a></div><div class="date">{day.day}, {month}. a las 20:05</div>
        <div class="place">Centro comercial Atlántico, Vecindario</div>
        <span class="bg-gray-200">Gratuito</span></div>'''
        e=app.extract_aguimes(BeautifulSoup(sample,"html.parser"))
        self.assertEqual(len(e),1)
        self.assertEqual(e[0]["municipality"],"Santa Lucía de Tirajana")
        self.assertEqual(e[0]["free"],1)

    def test_juventud_publishes_only_explicit_selector_sessions(self):
        a=app.TODAY+dt.timedelta(days=3)
        b=app.TODAY+dt.timedelta(days=10)
        sample=f'''<div class="event">
            <div class="name"><a href="https://actividadesjuventud.laspalmasgc.es/events/official">COSTURA CREATIVA</a></div>
            <div class="date">mié. 30, sep. - mié. 25, nov. a las 17:00</div>
            <div class="place">La Grada</div><span class="bg-gray-200">Gratuito</span>
            <select name="reserved_at">
              <option value="{a.isoformat()} 17:00:00">Plazas</option>
              <option value="{b.isoformat()} 17:00:00">Plazas</option>
              <option value="{b.isoformat()} 17:00:00">Repetida</option>
              <option value="__more__">Otras fechas</option>
              <option value="2026-02-31 17:00:00">Fecha imposible</option>
            </select></div>'''
        entries=app.extract_juventud(BeautifulSoup(sample,"html.parser"))
        self.assertEqual([e["start"] for e in entries],[a.isoformat()+"T17:00:00",b.isoformat()+"T17:00:00"])
        self.assertTrue(all(e["venue"]=="La Grada" and e["free"]==1 for e in entries))
        self.assertEqual(len({app.dedup_key(e) for e in entries}),2)

    def test_juventud_does_not_guess_schedules_from_broad_range(self):
        sample='''<div class="event"><div class="name">
          <a href="https://actividadesjuventud.laspalmasgc.es/events/official">Actividad semanal</a>
          </div><div class="date">lun. 02, nov. - lun. 23, nov. a las 17:00</div>
          <div class="place">La Grada</div><select name="reserved_at">
          <option value="__more__">Otras fechas</option></select></div>'''
        self.assertEqual(app.extract_juventud(BeautifulSoup(sample,"html.parser")),[])

    def test_juventud_ignores_past_and_distant_booking_slots(self):
        good=app.TODAY+dt.timedelta(days=2)
        past=app.TODAY-dt.timedelta(days=1)
        distant=app.TODAY+dt.timedelta(days=181)
        sample=f'''<div class="event"><div class="name">
          <a href="https://actividadesjuventud.laspalmasgc.es/events/official">AJEDREZ EN LA GRADA</a>
          </div><div class="date">sáb. 23, may. - sáb. 26, dic. a las 10:00</div>
          <div class="place">La Grada</div><select name="reserved_at">
          <option value="{past.isoformat()} 10:00:00">Pasado</option>
          <option value="{good.isoformat()} 10:00:00">Verificado</option>
          <option value="{distant.isoformat()} 10:00:00">Lejano</option>
          </select></div>'''
        items=app.extract_juventud(BeautifulSoup(sample,"html.parser"))
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["start"],good.isoformat()+"T10:00:00")

    def test_invalid_date_and_cross_source_dedup(self):
        with self.assertRaises(ValueError):
            app.iso_start(35,11,2026,"10:00")
        with sqlite3.connect(":memory:") as c:
            c.row_factory=sqlite3.Row
            app.init(c)
            e={"title":"Concierto prueba","start":app.TODAY.isoformat()+"T20:00:00","end":None,
                "municipality":"Ingenio","venue":"Recinto","category":"musica","free":None,
                "price":"","details":"","source_name":"Ayuntamiento","source_url":"https://ingenio.es/events/test",
                "status":"approved"}
            self.assertEqual(app.upsert(c,e),"added")
            self.assertEqual(app.upsert(c,e),"unchanged")
            self.assertEqual(c.execute("SELECT COUNT(*) FROM events").fetchone()[0],1)
            e["venue"]="Nuevo recinto"
            self.assertEqual(app.upsert(c,e),"changed")
            self.assertEqual(c.execute("SELECT venue FROM events").fetchone()[0],"Nuevo recinto")

if __name__=="__main__":unittest.main()
