import datetime as dt
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import official_stage_agendas as stages
import municipal_listing_dedup as reconcile
import sync_events

SAMPLE="""<section>
<div class="agenda_evento">
 <div class="agenda_tituloevento"><span>JAZZ OTOÑO 2026 - JUDITH HILL QUARTET</span></div>
 <div class="calendar_zonaevento">Las Palmas de Gran Canaria, <b>Teatro Cuyás</b></div>
 <a href="evento-770-jazz-otono-2026.html">Enlace</a>
 <table class="mtable"><tr><th>Fecha</th><th>Hora</th></tr>
 <tr><td><div>sábado 07/11/2026</div></td><td><span>19:30</span></td></tr>
 </table>
</div>
<div class="agenda_evento">
 <div class="agenda_tituloevento"><span>GRAN CANARIA BIG BAND & MATT FORBES</span></div>
 <div class="calendar_zonaevento">Las Palmas de Gran Canaria, <b>Teatro Cuyás</b></div>
 <a href="evento-775-gran-canaria-big.html">Enlace</a>
 <table class="mtable">
 <tr><td>viernes 18/12/2026</td><td>19:30</td></tr>
 <tr><td>sábado 19/12/2026</td><td>19:30</td></tr>
 </table>
</div>
<div class="agenda_evento">
 <div class="agenda_tituloevento"><span>VENTA DE ENTRADAS 2026-27</span></div>
 <div class="calendar_zonaevento"><b>Teatro Cuyás</b></div>
 <a href="evento-777-abonos.html">Enlace</a>
 <table class="mtable"><tr><td>jueves 31/12/2026</td><td>19:30</td></tr></table>
</div>
<div class="agenda_evento">
 <div class="agenda_tituloevento"><span>Concierto sin horario claro</span></div>
 <div class="calendar_zonaevento"><b>Sala Insular de Teatro</b></div>
 <a href="evento-888-show.html">Enlace</a>
 <table class="mtable"><tr><td>viernes 20/11/2026</td><td>19:30</td></tr></table>
</div>
</section>"""


WP_SAMPLE="""<section class="programacion">
 <div class="e-loop-item sala-teatro-cuyas genero-teatro"><div class="cy-tarjeta">
  <div class="cy-tarjeta__imagen"><img src="https://teatrocuyas.com/wp-content/uploads/2026/10/event_771-1-768x432.jpg"></div>
  <div class="cy-tarjeta__titulo"><h3><a href="https://teatrocuyas.com/espectaculo/flamenc-oh-de-yllana/">Flamenc Oh!</a></h3></div>
  <ul class="cuyas-mini-funciones">
   <li><span>Vie 13/11</span><span>19:30 h</span><span>1 h 30 min</span></li>
   <li><span>Sáb 14/11</span><span>19:30 h</span><span>1 h 30 min</span></li>
  </ul>
 </div></div>
 <div class="e-loop-item sala-teatro-cuyas genero-teatro"><div class="cy-tarjeta">
  <div class="cy-tarjeta__titulo"><h3><a href="https://teatrocuyas.com/espectaculo/largo-viaje-hacia-la-noche-de-eugene-oneill/">Largo viaje hacia la noche</a></h3></div>
  <ul class="cuyas-mini-funciones"><li><span>Vie 15/1</span><span>19:30 h</span></li></ul>
 </div></div>
 <div class="e-loop-item sala-teatro-cuyas genero-teatro"><div class="cy-tarjeta">
  <div class="cy-tarjeta__titulo"><h3><a href="https://evil.example/espectaculo/inventado/">Inventado fuera del teatro</a></h3></div>
  <ul class="cuyas-mini-funciones"><li><span>Vie 20/11</span><span>19:30 h</span></li></ul>
 </div></div>
 <div class="e-loop-item sala-insular-de-teatro genero-teatro"><div class="cy-tarjeta">
  <div class="cy-tarjeta__titulo"><h3><a href="https://teatrocuyas.com/espectaculo/otro-hall/">Acto de otra sala</a></h3></div>
  <ul class="cuyas-mini-funciones"><li><span>Vie 20/11</span><span>19:30 h</span></li></ul>
 </div></div>
 <div class="e-loop-item sala-teatro-cuyas genero-teatro"><div class="cy-tarjeta">
  <div class="cy-tarjeta__titulo"><h3><a href="https://teatrocuyas.com/espectaculo/hora-incorrecta/">Hora incorrecta</a></h3></div>
  <ul class="cuyas-mini-funciones"><li><span>Dom 20/11</span><span>19:30 h</span></li></ul>
 </div></div>
</section>"""

class StageConnectorTests(unittest.TestCase):
 def test_extract_individual_future_shows_skip_marketing_and_wrong_hall(self):
    rows,stats=stages.extract(BeautifulSoup(SAMPLE,"html.parser"),
        stages.SOURCES[0],dt.date(2026,10,28))
    self.assertEqual(len(rows),3)
    self.assertEqual(stats["cards_checked"],4)
    self.assertEqual([x["start"] for x in rows],
       ["2026-11-07T19:30:00","2026-12-18T19:30:00","2026-12-19T19:30:00"])
    self.assertTrue(all(x["free"] is None and x["price"]=="" for x in rows))
    self.assertTrue(all(x["venue"]=="Teatro Cuyás" for x in rows))
    rows,_=stages.extract(BeautifulSoup(SAMPLE,"html.parser"),
        stages.SOURCES[0],dt.date(2027,1,1))
    self.assertEqual(rows,[])

 def test_new_wordpress_cuyas_agenda_with_year_rollover_and_original_images(self):
    self.assertEqual(stages.SOURCES[0]["url"],"https://teatrocuyas.com/programacion/")
    rows,stats=stages.extract(BeautifulSoup(WP_SAMPLE,"html.parser"),
        stages.SOURCES[0],dt.date(2026,11,7))
    self.assertEqual(stats["cards_checked"],5)
    self.assertEqual(stats["cards_skipped"],3)
    self.assertEqual([e["start"] for e in rows],
        ["2026-11-13T19:30:00","2026-11-14T19:30:00","2027-01-15T19:30:00"])
    self.assertTrue(all(e["source_name"]=="Teatro Cuyás · agenda oficial" for e in rows))
    self.assertTrue(all(e["venue"]=="Teatro Cuyás" for e in rows))
    self.assertEqual(rows[0]["image_url"],
        "https://teatrocuyas.com/wp-content/uploads/2026/10/event_771-1-768x432.jpg")
    self.assertEqual(rows[0]["image_status"],"official_remote")
    self.assertEqual(rows[2]["image_url"],"")

 def test_cuyas_wordpress_rejects_bad_weekday_and_out_of_window(self):
    self.assertIsNone(stages.wp_session_day(20,11,"Dom",dt.date(2026,11,7)))
    self.assertIsNone(stages.wp_session_day(30,2,"Lun",dt.date(2026,11,7)))
    self.assertIsNone(stages.wp_session_day(20,11,"Vie",dt.date(2027,1,1)))
    self.assertEqual(stages.wp_session_day(15,1,"Vie",dt.date(2026,11,7)),
                     dt.date(2027,1,15))
    self.assertFalse(stages.expected_url(
        "https://teatrocuyas.com/espectaculo/obra/?utm_source=ad",
        "https://teatrocuyas.com",stages.WP_DETAIL))
    self.assertFalse(stages.expected_url(
        "https://teatrocuyas.com/other/obra/",
        "https://teatrocuyas.com",stages.WP_DETAIL))

 def test_first_party_stage_precedence_only_for_same_title_day_and_hour(self):
    def event(id,name,start,venue,source,url):
        return {"id":id,"title":name,"start":start,"venue":venue,
                "municipality":"Las Palmas de Gran Canaria",
                "source_name":source,"source_url":url}
    official=event(1,"JAZZ OTOÑO 2026 - JUDITH HILL QUARTET",
                   "2026-11-07T19:30:00","Teatro Cuyás",
                   "Teatro Cuyás · agenda oficial",
                   "https://teatrocuyas.com/evento-770-jazz-otono-2026.html")
    duplicate=event(2,official["title"],"2026-11-07",
                    "Sala Insular de Teatro",
                    "Portal oficial de Eventos Gran Canaria (Cabildo)",
                    "https://www.eventosgrancanaria.com/event/E-20261107-0001/acto")
    distinct=event(3,official["title"],"2026-11-07T21:00:00",
                   "Teatro Pérez Galdós",duplicate["source_name"],
                   "https://www.eventosgrancanaria.com/event/E-20261107-0002/acto")
    rows=reconcile.reconcile([official,duplicate,distinct],sync_events.norm)
    self.assertEqual({x["id"] for x in rows},{1,3})
    # Matching both title/day but another known hour is a separate session.
    rows=reconcile.reconcile([official,distinct],sync_events.norm)
    self.assertEqual({x["id"] for x in rows},{1,3})

 def test_https_origin_and_no_faked_links(self):
    spec=stages.SOURCES[0]
    self.assertTrue(stages.expected_url(
        "https://teatrocuyas.com/evento-775-gran-canaria-big.html",
        spec["site"],r"/evento-\d+-[a-z0-9-]+\.html"))
    self.assertFalse(stages.expected_url(
        "https://teatrocuyas.com.evil.com/evento-775-gran-canaria-big.html",
        spec["site"],r"/evento-\d+-[a-z0-9-]+\.html"))
    self.assertFalse(stages.expected_url(
        "http://teatrocuyas.com/evento-775-gran-canaria-big.html",
        spec["site"],r"/evento-\d+-[a-z0-9-]+\.html"))

if __name__=="__main__":unittest.main()
