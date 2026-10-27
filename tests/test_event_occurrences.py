"""Daily occurrences without fabricating a long-running course timetable."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import event_occurrences as oc
import municipal_listing_dedup as dup
from sync_events import norm

def ev(id=101,title="Feria artesanal",start="2026-10-28",end="2026-10-29",
       source="Ayuntamiento de Artenara · agenda",
       venue="Plaza de San Matías",municipality="Artenara",**kw):
    return dict(id=id,title=title,start=start,end=end,source_name=source,
                municipality=municipality,venue=venue,
                price="",free=None,source_url="https://example.org/feria/",**kw)

class DailyOccurrencesTests(unittest.TestCase):
    def test_two_days_are_two_cards(self):
        src=ev()
        items=oc.expand([src],dt.date(2026,10,27))
        self.assertEqual([i["start"] for i in items],["2026-10-28","2026-10-29"])
        self.assertEqual([i["occurrence_date"] for i in items],["2026-10-28","2026-10-29"])
        self.assertEqual([i["id"] for i in items],[101,oc.daily_occurrence_id(101,dt.date(2026,10,29))])
        self.assertNotEqual(items[0]["id"],items[1]["id"])
        self.assertEqual([i["series_end"] for i in items],["2026-10-29"]*2)
        self.assertTrue(all(i["end"] is None for i in items))
        self.assertEqual(src["end"],"2026-10-29")
    def test_towns_not_crossed(self):
        a=ev(id=101)
        b=ev(id=102,municipality="Telde")
        out=oc.expand([a,b],dt.date(2026,10,27))
        self.assertEqual(len(out),4)
        self.assertEqual(len({i["id"] for i in out}),4)
    def test_daily_ids_stable_across_runs(self):
        a=oc.expand([ev()],dt.date(2026,10,27))
        b=oc.expand([ev()],dt.date(2026,10,28))
        c=oc.expand([ev()],dt.date(2026,10,29))
        self.assertEqual(a[1]["id"],b[1]["id"])
        self.assertEqual(a[1]["id"],c[0]["id"])
        self.assertEqual(len(c),1)
    def test_long_exhibition_stays_active_range(self):
        long=ev(id=99,title="Exposición de octubre",start="2026-10-01",end="2026-10-31")
        e=oc.expand([long],dt.date(2026,10,27))
        self.assertEqual(e,[long])
        # Matches the browser's date-range check for each day in the month.
        for date in ("2026-10-01","2026-10-10","2026-10-27","2026-10-31"):
            self.assertTrue(e[0]["start"][:10]<=date<=e[0]["end"][:10])
        self.assertFalse(e[0]["start"][:10]<="2026-11-01"<=e[0]["end"][:10])
    def test_nine_month_course_not_invented_daily(self):
        long=ev(title="Curso dibujo",start="2026-10-01",end="2027-07-01")
        self.assertEqual(oc.expand([long],dt.date(2026,10,27)),[long])
    def test_overnight_performance_not_two_fictional_shows(self):
        event=ev(start="2026-10-28T23:00:00",end="2026-10-29T02:00:00")
        self.assertFalse(oc.should_split(event))
        self.assertEqual(oc.expand([event],dt.date(2026,10,27)),[event])
    def test_single_timed_first_day_and_date_only_end_no_guess(self):
        e=ev(start="2026-10-28T19:00:00",end="2026-10-29")
        self.assertFalse(oc.should_split(e))
    def test_not_turn_registration_window_into_daily_classes(self):
        e=ev(title="Plazo de inscripción para taller",start="2026-10-28",end="2026-10-29")
        self.assertFalse(oc.should_split(e))
    def test_separate_verified_sessions_same_day_kept(self):
        a=ev(id=21,title="Teatro infantil",start="2026-10-28T17:00:00",end=None)
        b=ev(id=22,title="Teatro infantil",start="2026-10-28T20:00:00",end=None)
        result=dup.reconcile(oc.expand([a,b],dt.date(2026,10,27)),norm)
        self.assertEqual(len(result),2)
    def test_cabildo_duplicate_matches_day_28_not_29(self):
        range_event=ev(id=50,source="Ayuntamiento de Artenara · agenda")
        repeated=ev(id=51,source="Portal oficial de Eventos Gran Canaria (Cabildo)",
                    start="2026-10-28",end=None)
        res=dup.reconcile(oc.expand([range_event,repeated],dt.date(2026,10,27)),norm)
        self.assertEqual(len(res),2)
        self.assertEqual({v["start"][:10] for v in res},{"2026-10-28","2026-10-29"})
    def test_next_day_two_sources_reconcile_only_next_day(self):
        ranged=ev(id=51)
        listing=ev(id=52,source="Portal oficial de Eventos Gran Canaria (Cabildo)",
                   start="2026-10-29",end=None)
        out=dup.reconcile(oc.expand([ranged,listing],dt.date(2026,10,27)),norm)
        self.assertEqual(len(out),2)
        self.assertEqual(len([x for x in out if x["start"][:10]=="2026-10-29"]),1)
        self.assertEqual(len([x for x in out if x["start"][:10]=="2026-10-28"]),1)
if __name__=="__main__":
    unittest.main()
