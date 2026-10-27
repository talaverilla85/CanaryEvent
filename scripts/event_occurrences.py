"""Project a verified short date range into a card for each calendar day.

Rules:
* A 2- or 3-day date-only programme with a named venue can produce daily
  occurrences; only dates explicitly bounded by the source are used.
* The first day retains the existing integer id for saved-plan compatibility.
  Subsequent days get deterministic negative integer ids from parent/day.
* Overnight performances (start/end with times) remain ONE event, not two
  fabricated sessions.
* Long-running activities remain ONE range record, continuously visible
  through the existing inFilter() logic. A ten-month course is not assumed
  to run on every day of its advertised enrolment period.
* Never derive a time of day for an unspecified session.
"""
from __future__ import annotations
import datetime as dt

MAX_DAILY_DAYS = 3
# Dates are intentionally bounded to the future; keep an event's first
# day as the original id, and avoid resurrecting days already in the past.
def date_of(value):
    return dt.date.fromisoformat(str(value)[:10])

def should_split(event):
    raw_start=str(event.get("start") or "")
    raw_end=str(event.get("end") or "")
    if not raw_start or not raw_end:return False
    try:
        first,last=date_of(raw_start),date_of(raw_end)
    except ValueError:return False
    days=(last-first).days+1
    if days<2 or days>MAX_DAILY_DAYS:return False
    # One-night performance can end past midnight; its two calendar dates
    # do NOT certify two performances.
    if "T" in raw_start or "T" in raw_end:return False
    lowered=str(event.get("title") or "").lower()
    if any(x in lowered for x in (
       "inscripción","inscripcion","matrícula","matricula","plazo",
       "solicitudes","convocatoria","inscripciones","registro")):
        return False
    return True

def daily_occurrence_id(original_id,day):
    result=-(int(original_id)*100_000_000+int(day.strftime("%Y%m%d")))
    if abs(result)>=2**53:raise ValueError("ID de jornada fuera del rango JS")
    return result

def expand(events,today):
    today=dt.date.fromisoformat(today) if isinstance(today,str) else today
    result=[]
    for e in events:
        if not should_split(e):
            result.append(e)
            continue
        start,end=date_of(e["start"]),date_of(e["end"])
        for index in range((end-start).days+1):
            day=start+dt.timedelta(days=index)
            if day<today:continue
            item=dict(e)
            item["series_id"]=e["id"]
            item["series_start"]=e["start"]
            item["series_end"]=e["end"]
            item["occurrence_date"]=day.isoformat()
            item["occurrence_day"]=index+1
            item["occurrence_count"]=(end-start).days+1
            # Keep a verified first-day time only. Subsequent days have no
            # verified time unless the source explicitly lists another session.
            item["start"]=e["start"] if index==0 else day.isoformat()
            # End is now this particular date, not the whole programme.
            # Never reuse the end-time of the final day as a first-day time.
            item["end"]=None
            item["id"]=e["id"] if index==0 else daily_occurrence_id(e["id"],day)
            result.append(item)
    return sorted(result,key=lambda e:(str(e.get("start") or ""),int(e["id"])))

def metrics(before,after):
    return {
      "raw_events":len(before),
      "daily_cards":len(after),
      "short_ranges_expanded":sum(should_split(e) for e in before),
      "extra_daily_cards":max(0,len(after)-len(before)),
      "long_ranges_preserved":sum(
        bool(e.get("end")) and not should_split(e) and
        str(e["end"])[:10]>str(e["start"])[:10] for e in before)
    }
