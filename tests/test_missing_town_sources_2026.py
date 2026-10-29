"""The current 2026 programme is audited, but sources with robots bans are NOT crawled.

Moya brochure: https://www.villademoya.es/cmsAdmin/uploads/OTO_O_es_Cultura_2026.pdf
Valsequillo calendar: linked from official municipal calendar page.
Mogán notice: official 27 October 2026 press release.
"""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import moya_autumn_agenda as moya
import valsequillo_calendar as vals
import mogan_confirmed_news as mogan
import firgas_local_confirmed as firgas
import sync_events as app

TODAY=dt.date(2026,10,29)
class MissingTownReviewTests(unittest.TestCase):
    def test_moya_exact_2026_brochure_dates_venues_and_no_recurring_2027(self):
        events,stat=moya.fetch_and_extract(TODAY,app.PLACES)
        self.assertEqual(len(events),7)
        self.assertEqual(stat["method"],"manually_reviewed_pdf_2026_no_bot_crawl")
        self.assertEqual({x["start"][:10] for x in events},
                         {"2026-10-31","2026-11-06","2026-11-08","2026-11-09",
                          "2026-11-13","2026-11-15","2026-11-20"})
        self.assertTrue(all(x["municipality"]=="Moya" for x in events))
        self.assertTrue(all(x["venue"] and "Consultar" not in x["venue"] for x in events))
        self.assertEqual(moya.fetch_and_extract(dt.date(2026,12,1),app.PLACES)[0],[])
        self.assertEqual(moya.fetch_and_extract(dt.date(2027,10,29),app.PLACES)[0],[])

    def test_valsequillo_public_ics_one_off_event_snapshot(self):
        events,info=vals.fetch_and_extract(TODAY,app.PLACES)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["start"],"2026-10-30T18:00:00")
        self.assertIn("Biblioteca Municipal",events[0]["venue"])
        self.assertEqual(info["method"],"manually_verified_calendar_2026_no_bot_crawl")
        self.assertEqual(vals.fetch_and_extract(dt.date(2026,11,1),app.PLACES)[0],[])
        self.assertEqual(vals.fetch_and_extract(dt.date(2027,10,29),app.PLACES)[0],[])

    def test_calendar_parser_guards_year_cancelled_recurring_and_admin(self):
        source="""BEGIN:VCALENDAR
X-WR-CALNAME:ACTIVIDADES MUNICIPALES
BEGIN:VEVENT
UID:one
DTSTART:20261030T180000Z
SUMMARY:Circuito narración oral
LOCATION:Biblioteca Municipal\\, Valsequillo
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20261030T180000Z
SUMMARY:Visita Unidad Movil de la Policia Nacional DNI
LOCATION:Plaza de Tifariti\\, Valsequillo
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20261030T180000Z
SUMMARY:Otro evento cancelado
LOCATION:Biblioteca Municipal\\, Valsequillo
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""
        events,stats=vals.parse_ical(source,TODAY)
        self.assertEqual(len(events),1)
        self.assertEqual(stats["calendar_total"],3)
        self.assertEqual(events[0]["start"],"2026-10-30T18:00:00")
        self.assertEqual(events[0]["venue"],"Biblioteca Municipal")
        self.assertEqual(vals.parse_ical(source,dt.date(2027,1,1))[0],[])

    def test_mogan_unambiguous_press_release_no_guessed_time(self):
        rows,info=mogan.fetch_and_extract(TODAY,app.PLACES)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["start"],"2026-11-14T10:00:00")
        self.assertEqual(rows[0]["venue"].split(",")[0],"Plaza Pérez Galdós")
        self.assertEqual(rows[0]["free"],1)
        self.assertEqual(rows[0]["price"],"Gratis")
        self.assertEqual(mogan.fetch_and_extract(dt.date(2027,11,14),app.PLACES)[0],[])

    def test_firgas_independent_guides_not_mislabelled_municipal(self):
        events,meta=firgas.fetch_and_extract(TODAY,app.PLACES)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]["start"],"2026-10-31T21:00:00")
        self.assertEqual(events[0]["venue"],"Casa de los Mayores de Firgas")
        self.assertEqual(events[0]["price"],"Gratis")
        self.assertNotIn("Ayuntamiento",events[0]["source_name"])
        self.assertEqual(meta["corroborating_sources"],3)
        self.assertEqual(firgas.fetch_and_extract(dt.date(2026,11,1),app.PLACES)[0],[])
        self.assertEqual(firgas.fetch_and_extract(dt.date(2027,10,31),app.PLACES)[0],[])

    def test_all_four_sources_require_a_canonical_municipality(self):
        for mod,name in ((moya,"Moya"),(vals,"Valsequillo"),(mogan,"Mogán")):
            places={key:value for key,value in app.PLACES.items() if key!=name}
            self.assertEqual(mod.fetch_and_extract(TODAY,places)[0],[])

    def test_sources_are_wired_into_daily_sync_and_agenda_watchpaths(self):
        program=(ROOT/"scripts/sync_events.py").read_text(encoding="utf8")
        workflow=(ROOT/".github/workflows/sync-events.yml").read_text(encoding="utf8")
        for name in ("moya_autumn_agenda","valsequillo_calendar","mogan_confirmed_news","firgas_local_confirmed"):
            self.assertIn(name+".py",workflow)
        self.assertIn("for municipal_module in (moya_autumn_agenda",program)

if __name__=="__main__":
    unittest.main()
