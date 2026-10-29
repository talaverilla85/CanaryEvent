"""Official Moya Autumn 2026 programme, each event validated in its PDF page.

This is not a generic PDF-to-venue guessing tool: it is a fixed 2026
calendar verified against the Ayuntamiento's original eight-page brochure,
the document's printed year, date, clock and location on each page.
"""
import datetime as dt
import io
import re
import unicodedata
from urllib.robotparser import RobotFileParser

import requests
from pypdf import PdfReader

NAME="Ayuntamiento de Moya · Otoño es Cultura 2026"
ROOT="https://www.villademoya.es"
URL=ROOT+"/cmsAdmin/uploads/OTO_O_es_Cultura_2026.pdf"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT}
PLACE="Moya"
MAX_SIZE=5_000_000
# Date/time/place verified from the printed brochure (including the image).
# Require the original event and venue keywords in exactly the same page;
# page-level date/time pins are only used for the *specified* brochure.
EVENTS=(
 dict(title="Concierto del Cuarteto Parea",day="2026-10-31",time="19:30",
      venue="Cementerio Municipal de Moya",page=5,
      terms=("concierto","cuarteto parea","cementerio municipal","31","oct","19.30"),category="musica"),
 dict(title="Cuentacuentos del Circuito Insular de Narración Oral",day="2026-11-06",time="18:00",
      venue="Biblioteca Municipal de Moya",page=6,
      terms=("cuentacuentos","circuito","narracion oral","biblioteca municipal","6","nov","18.00"),category="familia"),
 dict(title="VII Concurso de Pintura Rápida SURCA 2026",day="2026-11-08",time="10:00",
      venue="Calles del casco de Moya",page=6,
      terms=("vii concurso de pintura","surca 2026","calles del casco","8","nov","10 a 17"),category="cultura"),
 dict(title="Exposición de obras del VII Concurso SURCA 2026",day="2026-11-09",time=None,
      end="2026-11-27",venue="Casa de la Cultura de Moya",page=6,
      terms=("exposicion de","concurso de","surca 2026","casa de la","cultura","9al","27","nov"),category="cultura"),
 dict(title="Mi sueño de invierno",day="2026-11-13",time="20:00",
      venue="Casa de la Cultura de Moya",page=7,
      terms=("mi sueno","de invierno","casa de","la cultura","13","nov","20.00"),category="cultura"),
 dict(title="Encuentro Insular de Bandas de Música de Gran Canaria",day="2026-11-15",time="12:30",
      venue="Plaza Tomás Morales, Moya",page=7,
      terms=("encuentro","insular de","bandas de","plaza tomas","morales","15","nov","12.30"),category="musica"),
 dict(title="Ananda · The Violin Band",day="2026-11-20",time="20:00",
      venue="Casa de la Cultura de Moya",page=7,
      terms=("ananda","the violin band","casa de","la cultura","20","nov","20.00"),category="musica"),
)

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").casefold())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())

def extract_pdf(raw,today):
    if len(raw)>MAX_SIZE or not raw.startswith(b"%PDF-"):
        raise ValueError("Unexpected Moya source PDF")
    p=PdfReader(io.BytesIO(raw),strict=False)
    if len(p.pages)!=8:raise ValueError("Unexpected Moya brochure layout")
    cover=norm((p.pages[0].extract_text() or "")+" "+(p.pages[1].extract_text() or ""))
    if "2026" not in cover:raise ValueError("Incorrect Moya programme year")
    text_by_page={i:norm(page.extract_text() or "") for i,page in enumerate(p.pages)}
    events=[]
    for x in EVENTS:
        first=dt.date.fromisoformat(x["day"])
        last=dt.date.fromisoformat(x.get("end",x["day"]))
        if not today<=last and not today<=first:continue
        if first>today+dt.timedelta(days=120):continue
        body=text_by_page[x["page"]]
        if any(norm(t) not in body for t in x["terms"]):
            raise ValueError("Moya PDF changed: event/date/place no longer verified: "+x["title"])
        events.append({
            "title":x["title"],
            "start":x["day"]+("T"+x["time"]+":00" if x.get("time") else ""),
            "end":x.get("end"),"municipality":PLACE,
            "venue":x["venue"],"category":x["category"],
            "free":None,"price":"",
            "details":"Programa cultural municipal Otoño es Cultura 2026. "
                      +"Consulta la programación oficial para accesos y condiciones.",
            "source_name":NAME,"source_url":URL,"status":"approved"})
    return events

def curated_2026(today):
    """Reviewer's manually verified 2026 PDF snapshot, no robot access.

    Page maps and exact printed dates/places are in EVENTS. Since the
    town's robots.txt disallows all paths, the daily job must never
    fetch the PDF. For 2027 a new authorised feed or human review is
    required; we NEVER roll these entries to another year.
    """
    rows=[]
    for x in EVENTS:
        first=dt.date.fromisoformat(x["day"])
        last=dt.date.fromisoformat(x.get("end",x["day"]))
        if last<today or first>today+dt.timedelta(days=120):continue
        rows.append({
            "title":x["title"],"start":x["day"]+("T"+x["time"]+":00" if x.get("time") else ""),
            "end":x.get("end"),"municipality":PLACE,"venue":x["venue"],
            "category":x["category"],"free":None,"price":"",
            "details":"Oto?o es Cultura 2026 (programa PDF municipal verificado manualmente). Condiciones y acceso en el folleto original.",
            "source_name":NAME,"source_url":URL,"status":"approved"})
    return rows

def fetch_and_extract(today,places,session=None):
    if PLACE not in places:return [],{"source":NAME,"found":0,"error":""}
    rows=curated_2026(today)
    return rows,{"source":NAME,"found":len(rows),"error":"",
                 "source_year":2026,"method":"manually_reviewed_pdf_2026_no_bot_crawl"}
