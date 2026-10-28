import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import official_culture_calendars as cult
import municipal_listing_dedup as dedup

DAY=dt.date(2026,10,28)
def soup(raw):
    return BeautifulSoup(raw,"html.parser")
def event(title,source,venue="Teatro Pérez Galdós",start="2026-11-10T20:00:00",idx=1):
    return dict(id=idx,title=title,start=start,venue=venue,
                municipality="Las Palmas de Gran Canaria",source_name=source)

class OfficialCulturalFeedTests(unittest.TestCase):
    def test_urls_exact_https_no_redirect_trick(self):
        self.assertTrue(cult.expected_url(
          "https://teatroperezgaldos.es/evento/el-fantasma-de-la-opera",
          cult.THEATRE_URL,r"/evento/[a-z0-9-]+"))
        for url in (
            "http://teatroperezgaldos.es/evento/musical",
            "https://teatroperezgaldos.es.evil.org/evento/musical",
            "https://user@teatroperezgaldos.es/evento/musical",
            "https://teatroperezgaldos.es/evento/musical?redirect=evil",
            "https://teatroperezgaldos.es:8443/evento/musical",
        ):
            self.assertFalse(cult.expected_url(url,cult.THEATRE_URL,
                                                r"/evento/[a-z0-9-]+"),url)

    def test_theatre_sessions_only_explicit_dates_and_times(self):
        fixture=soup("""
           <div class="event-shows__item">
             <p class="event-shows__date">S09 ENE 2027</p>
             <p class="event-shows__time">17:00</p></div>
           <div class="event-shows__item">
             <p class="event-shows__date">S09 ENE 2027</p>
             <p class="event-shows__time">21:00</p></div>
           <div class="event-shows__item">
             <p class="event-shows__date">D10 ENE 2027</p>
             <p class="event-shows__time">16:30</p></div>
           <div class="event-shows__item">
             <p class="event-shows__date">L11 ENE 2027</p></div>""")
        got=cult.theatre_sessions(fixture,DAY)
        self.assertEqual(len(got),2)
        self.assertEqual(got[dt.date(2027,1,9)],{"17:00","21:00"})
        self.assertNotIn(dt.date(2027,1,11),got)

    def test_theatre_session_aggregates_two_functions_not_fake_extra_event(self):
        landing=soup("""
          <article class="event-card"><time class="event-card__date">S09 ENE 2027 - D10 ENE 2027</time>
          <a href="/evento/el-fantasma-de-la-opera"></a>
          <h2 class="event-card__title">El Fantasma de la Ópera</h2></article>""")
        detail=soup("""
           <h2 class="page-header-event__title">El Fantasma de la Ópera</h2>
           <div class="page-header-event__description">El Musical</div>
           <div class="event-shows__item">
             <p class="event-shows__date">S09 ENE 2027</p>
             <p class="event-shows__time">17:00</p></div>
           <div class="event-shows__item">
             <p class="event-shows__date">S09 ENE 2027</p>
             <p class="event-shows__time">21:00</p></div>""")
        class FakeReader:
            def html(self,url,*args):
                return detail if "/evento/" in url else landing
        rows,stats=cult.extract_theatre(FakeReader(),DAY,lambda title:"cultura")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["start"],"2027-01-09T17:00:00")
        self.assertIn("17:00, 21:00",rows[0]["details"])
        self.assertEqual(rows[0]["category"],"musica")
        self.assertEqual(rows[0]["source_name"],cult.THEATRE_NAME)

    def test_theatre_landing_is_not_proof_without_session_detail(self):
        landing=soup("""<article class="event-card">
          <a href="/evento/unlisted-musical"></a>
          <h2 class="event-card__title">Unlisted Musical</h2>
          <time class="event-card__date">D01 NOV 2026</time></article>""")
        detail=soup('<h2 class="page-header-event__title">Unlisted Musical</h2>')
        class FakeReader:
            def html(self,url,*args):return detail if "/evento/" in url else landing
        with self.assertRaises(RuntimeError):
            cult.extract_theatre(FakeReader(),DAY,lambda title:"cultura")

    def test_lpa_parses_date_and_specific_place_but_rejects_itinerary(self):
        s=soup("""<div class="show-event">
          <div class="name"><a href="https://lpacultura.com/events/12-noches">12 noches de autor: Ida Susal</a></div>
          <div class="mt-2"><div class="pl-2">Mié. 28, Oct. de 19:00 - 20:30</div></div>
          <div class="mt-1"><div class="pl-2">Palacete Rodríguez Quegles</div></div>
          <div class="mt-1"><div class="pl-2">Gratuito</div></div>
          <div class="p-2"><div class="rounded-lg">Música</div></div></div>
        <div class="show-event">
          <div class="name"><a href="https://lpacultura.com/events/ruta">Ruta por Vegueta</a></div>
          <div class="mt-2"><div class="pl-2">Vie. 30, Oct. de 21:00 - 23:00</div></div>
          <div class="mt-1"><div class="pl-2">Barrio Vegueta (Recorrido por varias plazas)</div></div></div>""")
        rows=cult.extract_lpa(s,DAY,lambda title:"cultura")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["start"],"2026-10-28T19:00:00")
        self.assertEqual(rows[0]["venue"],"Palacete Rodríguez Quegles")
        self.assertEqual(rows[0]["free"],1)
        self.assertEqual(rows[0]["price"],"Gratis")

    def test_philharmonic_does_not_infer_missing_hall_or_date(self):
        s=soup("""<a class="card-article" href="/programacion/conciertos/first">
          <time class="card-article__date">18 de diciembre 2026 - 19:30h.</time>
          <div class="card-article__location">Teatro Cuyás</div>
          <h2 class="card-article__title">Gran Canaria Big Band &amp; Matt Forbes</h2></a>
          <a class="card-article" href="/programacion/conciertos/unknown">
          <time class="card-article__date">18 de diciembre 2026 - 19:30h.</time>
          <h2 class="card-article__title">No venue</h2></a>""")
        rows=cult.extract_philharmonic(s,DAY)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["venue"],"Teatro Cuyás")
        self.assertEqual(rows[0]["start"],"2026-12-18T19:30:00")
        self.assertIsNone(rows[0]["free"])

    def test_organizer_can_suppress_conflicting_reposted_same_named_event(self):
        a=event("Festival de magia: El gran espectáculo",
                cult.LPA_NAME,"Auditorio José Antonio Ramos",idx=11)
        b=event("Festival de magia: El gran espectáculo",
                "Portal oficial de Eventos Gran Canaria (Cabildo)",
                "Espacio Cultural Jesús Arencibia",start="2026-11-10T21:00:00",idx=12)
        kept=dedup.reconcile([a,b],lambda text:cult.norm(text))
        self.assertEqual([x["id"] for x in kept],[11])

    def test_different_named_versions_of_same_documented_concert(self):
        a=event("Concierto Aniversario de la Sociedad Filarmónica de Las Palmas",
                cult.PHILHARMONIC_NAME,idx=10)
        b=event("Concierto Aniversario",cult.THEATRE_NAME,idx=11)
        got=dedup.reconcile([a,b],cult.norm)
        self.assertEqual([x["id"] for x in got],[10])

    def test_narrow_repertoire_alias_requires_exact_hall_and_date(self):
        a=event("Grandes obras del repertorio ruso: Shostakovich y Mussorgsky",
                cult.PHILHARMONIC_NAME,venue="Auditorio Alfredo Kraus",
                start="2026-11-12T20:00:00",idx=14)
        b=event("Chichon dirige Shostakovich y Mussorgski",
                "Portal oficial de Eventos Gran Canaria (Cabildo)",
                venue="Auditorio Alfredo Kraus",start="2026-11-12",idx=15)
        self.assertEqual(len(dedup.reconcile([a,b],cult.norm)),1)
        not_same=event("Chichon dirige Shostakovich y Mussorgski",
                "Portal oficial de Eventos Gran Canaria (Cabildo)",
                venue="Otro teatro",start="2026-11-12",idx=16)
        self.assertEqual(len(dedup.reconcile([a,not_same],cult.norm)),2)

    def test_unrelated_titles_or_multiple_promoters_never_override(self):
        a=event("Festival Música Viva",cult.LPA_NAME,idx=11)
        b=event("Gala escolar", "Portal oficial de Eventos Gran Canaria (Cabildo)",idx=12)
        self.assertEqual(len(dedup.reconcile([a,b],cult.norm)),2)
        other=event("Festival Música Viva",cult.THEATRE_NAME,"Otro teatro",idx=13)
        copied=event("Festival Música Viva","Portal oficial de Eventos Gran Canaria (Cabildo)",
                     "Plaza municipal",idx=14)
        self.assertEqual(len(dedup.reconcile([a,other,copied],cult.norm)),3)

if __name__=="__main__":
    unittest.main()
