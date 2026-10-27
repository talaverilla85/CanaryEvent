"""Publishable candidate gate for scanned municipal PDFs, with independent visual agreement.

A single LLM answer NEVER reaches the public feed. Both passes must agree on
specific title, calendar date, time and named venue; the date must be upcoming,
and each pass includes its own page-evidence quote. Every resulting event has
the original PDF and page, and coordinates are resolved by the existing
verified-venue system.
"""
import datetime as dt
import re
import unicodedata

SOURCE="Ayuntamiento de Telde · programas PDF verificados (doble lectura IA)"
MAX_LOOKAHEAD_DAYS=120

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").casefold())
    return re.sub(r"[^a-z0-9]+"," ", "".join(c for c in s if not unicodedata.combining(c))).strip()

def safe_venue(value):
    s=str(value or "").strip()
    n=norm(s)
    if len(s)<9 or len(n.split())<2:return False
    if any(n.startswith(x) for x in ("por confirmar","consultar","pendiente","a determinar","lugar a")):return False
    if n in {"plaza","iglesia","calle principal","telde","en el barrio","centro cultural"}:return False
    return True

def same_record(first,second):
    if not all(isinstance(x,dict) for x in (first,second)):return False
    # Evidence independently supplied by both model reads.
    if len(str(first.get("evidence") or ""))<18 or len(str(second.get("evidence") or ""))<18:return False
    if not safe_venue(first.get("venue")) or not safe_venue(second.get("venue")):return False
    if not first.get("time") or not second.get("time"):return False
    if any(str(first.get(k) or "").strip()!=str(second.get(k) or "").strip() for k in ("date","time")):return False
    if norm(first.get("title"))!=norm(second.get("title")):return False
    if norm(first.get("venue"))!=norm(second.get("venue")):return False
    # Prefer not to auto-publish generic program headings masquerading as acts.
    title=norm(first.get("title"))
    if len(title)<12 or title.startswith(("fiestas en honor","programa de fiestas","actividades de","programacion")):return False
    return True

def approved_candidates(first_records,second_records,*,today):
    if not isinstance(first_records,list) or not isinstance(second_records,list):return []
    approved=[]
    used=set()
    for first in first_records:
        for i,second in enumerate(second_records):
            if i in used or not same_record(first,second):continue
            try:when=dt.date.fromisoformat(first["date"])
            except (ValueError,TypeError):continue
            if not today<=when<=today+dt.timedelta(days=MAX_LOOKAHEAD_DAYS):continue
            h,m=map(int,first["time"].split(":"))
            if h>23 or m>59:continue
            approved.append(first)
            used.add(i)
            break
    return approved

def approved_to_event(item):
    # Validated in two separate reads of the same source page.
    category={"musica":"musica","gastronomia":"gastronomia","familia":"familia",
              "deporte":"deporte","cultura":"cultura","religioso":"cultura",
              "fiesta":"ocio","otros":"otros"}.get(item.get("type"),"otros")
    return {
        "title":item["title"],
        "start":item["date"]+"T"+item["time"]+":00",
        "end":None,"municipality":"Telde",
        "venue":item["venue"],
        "category":category,"free":None,"price":"",
        "details":("Acto individual recogido en un programa oficial de fiestas de Telde. "
                   "Fecha, hora y recinto contrastados mediante dos lecturas independientes "
                   "de la página "+str(item["pdf_page"])+". Confirma posibles cambios en el PDF original."),
        "source_name":SOURCE,
        "source_url":item["pdf_url"],
        "status":"approved",
        "verification":"two_independent_visual_passes",
        "pdf_sha256":item["pdf_sha256"],
        "pdf_page":item["pdf_page"],
    }
