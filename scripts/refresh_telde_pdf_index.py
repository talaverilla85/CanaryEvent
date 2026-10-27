"""Refresh the official Telde PDF inventory before the AI extraction job.

The full events sync normally does this after the AI stage; this lightweight
step avoids an extra day's delay when a new festival PDF is published.
Nothing here claims a PDF is an event or guesses a date.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import telde_barrio_programs as pdf_index

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"public"/"municipal_programs.json"

def update(*,today=None,fetch=pdf_index.fetch_year):
    today=today or dt.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    year=today.year
    page=fetch(year)
    programs=pdf_index.extract(page,year)
    old={}
    if OUTPUT.exists():
        try:old=json.loads(OUTPUT.read_text(encoding="utf8"))
        except (ValueError,OSError):old={}
    checked=dt.datetime.now(dt.timezone.utc).isoformat()
    merged=pdf_index.merge_seen(programs,old.get("programs",[]),checked)
    result={
        "checked_at":checked,
        "source_name":pdf_index.NAME,
        "source_url":pdf_index.index_url(year),
        "program_count":len(merged),
        "events_imported":int(old.get("events_imported") or 0),
        "note":"Se han descubierto programas PDF municipales; cada actividad requiere lectura y comprobación de su fecha.",
        "programs":merged,
    }
    tmp=OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    tmp.replace(OUTPUT)
    print(f"Official Telde PDFs: {len(merged)} indexed, {len(merged)-len(old.get('programs',[]))} net change")
    return result

if __name__=="__main__":
    update()
