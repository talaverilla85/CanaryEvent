"""Allowlisted official PDF-program discovery for three Gran Canaria municipalities.

Discovery is document inventory only. A PDF link is never treated as an event.
Known 2026 programme end dates were checked against the official cover pages;
they are historical scheduling hints, not per-event assertions.
"""
from __future__ import annotations
import datetime as dt
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

UA="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
SOURCES={
 "Santa Lucía de Tirajana":{
  "host":"www.santaluciagc.com",
  "landing":"https://www.santaluciagc.com/fiestas-san-rafael-{year}/",
  "link_pattern":r"programa.*san.?rafael|san.?rafael.*programa",
  "known_end":{"2026":"2026-11-01"},
  "known_pdf":{"2026":"https://www.santaluciagc.com/wp-content/uploads/2026/10/Programa_Fiestas-SanRafael_2026_web-1.pdf"},
 },
 "Agüimes":{
  "host":"aguimes.es",
  "landing":"https://aguimes.es/festejos/",
  "link_pattern":r"fiestas.*(?:rosario|guayadeque|programa|202[0-9])",
  "known_end":{"2026":"2026-10-13"},
  "known_pdf":{"2026":"https://aguimes.es/wp-content/uploads/2026/09/AF_FIESTAS-DEL-ROSARIO-2026-DIGITAL.pdf"},
 },
 "Gáldar":{
  "host":"www.galdar.es",
  "landing":"https://www.galdar.es/fiestas/",
  "link_pattern":r"programa.*(?:santiago|fiestas)|fiestas.*santiago.*programa",
  "known_end":{"2026":"2026-07-26"},
  "known_pdf":{"2026":"https://www.galdar.es/wp-content/uploads/2026/06/PROGRAMA-FIESTAS-DE-SANTIAGO-2026.pdf"},
 },
}
def verified_pdf(url: str, municipality: str, year: int):
    spec=SOURCES[municipality]
    parts=urlsplit(str(url))
    return (parts.scheme=="https" and parts.hostname==spec["host"]
            and not (parts.username or parts.password or parts.port or parts.query or parts.fragment)
            and bool(re.fullmatch(
               r"/wp-content/uploads/"+str(year)+r"/(?:0[1-9]|1[0-2])/[a-zA-Z0-9_.%-]+\.pdf",
               parts.path,re.I)))
def robots_for(session, host: str):
    response=session.get("https://"+host+"/robots.txt",timeout=15,
                         headers={"User-Agent":UA},allow_redirects=False)
    if response.status_code!=200:
        raise RuntimeError("Robots policy unavailable for "+host)
    parser=RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser
def discover(session, municipality: str, year: int):
    spec=SOURCES[municipality]
    page=spec["landing"].format(year=year)
    robots=robots_for(session,spec["host"])
    if not robots.can_fetch(UA,page):
        raise PermissionError("Municipal index blocked by robots.txt")
    response=session.get(page,timeout=25,allow_redirects=False,
                         headers={"User-Agent":UA})
    if response.status_code!=200:
        raise RuntimeError("Municipal index HTTP "+str(response.status_code))
    if len(response.content)>2_000_000:
        raise ValueError("Municipal index unexpectedly large")
    soup=BeautifulSoup(response.content,"html.parser")
    records={}
    for a in soup.select("a[href]"):
        url=urljoin(page,a.get("href","").strip())
        label=" ".join(a.get_text(" ",strip=True).split())
        label_and_path=label+" "+urlsplit(url).path.split("/")[-1].replace("-"," ")
        if not re.search(spec["link_pattern"],label_and_path,re.I):
            continue
        if not verified_pdf(url,municipality,year) or not robots.can_fetch(UA,url):
            continue
        # Never infer event dates from names, upload months or year.
        records[url]={"municipality":municipality,"title":label[:220] or "Programa municipal de fiestas",
                      "pdf_url":url,"year":year,"official_index_url":page,
                      "discovery":"official_html","event_date_verified":False}
    return list(records.values())
def known_2026():
    results=[]
    for municipality,spec in SOURCES.items():
        url=spec["known_pdf"]["2026"]
        assert verified_pdf(url,municipality,2026)
        results.append({"municipality":municipality,"title":"Programa oficial 2026 de "+municipality,
                        "pdf_url":url,"year":2026,
                        "official_index_url":spec["landing"].format(year=2026),
                        "discovery":"official_pdf_confirmed_2026",
                        "event_date_verified":False,
                        "program_end_hint":spec["known_end"]["2026"],
                        "program_end_evidence_url":url})
    return results
def build_catalog(year: int, session=None, *, existing=None):
    session=session or requests.Session()
    by_url={}
    errors={}
    for municipality in SOURCES:
        try:
            for entry in discover(session,municipality,year):
                by_url[entry["pdf_url"]]=entry
        except (RuntimeError,ValueError,PermissionError,requests.RequestException) as exc:
            errors[municipality]=type(exc).__name__+": "+str(exc)[:140]
    if year==2026:
        for known in known_2026():
            by_url.setdefault(known["pdf_url"],known)
    previous={e.get("pdf_url"):e for e in (existing or {}).get("programs",[])
              if isinstance(e,dict) and e.get("pdf_url")}
    checked=dt.datetime.now(dt.timezone.utc).isoformat()
    records=[]
    for url,entry in by_url.items():
        first_seen=previous.get(url,{}).get("first_seen_at",checked)
        row={**entry,"first_seen_at":first_seen}
        for known in known_2026() if year==2026 else []:
            if known["pdf_url"]==url:
                row["program_end_hint"]=known["program_end_hint"]
                row["program_end_evidence_url"]=url
        records.append(row)
    return {"checked_at":checked,"year":year,"scope":list(SOURCES),
            "errors":errors,"program_count":len(records),
            "events_imported":0,
            "note":"Official PDF inventory only. Unverified acts never enter the public calendar.",
            "programs":sorted(records,key=lambda p:(p["municipality"],p["pdf_url"]))}
