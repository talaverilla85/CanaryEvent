"""Read upcoming events published in Gáldar's official Culture calendar.

Uses HTML EventON schema.org date/time/location fields, not inferred text.
"""
from __future__ import annotations
import datetime as dt
import re
import requests
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

NAME="Ayuntamiento de Gáldar · agenda de Cultura"
URL="https://www.galdar.es/event-organizer/concejalia-de-cultura-del-ayuntamiento-de-galdar/"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT}
DATE=re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2})")

def parse_schema_date(value):
    if not value:return None
    m=DATE.match(value)
    if not m:return None
    try:return dt.datetime(*(int(v) for v in m.groups()))
    except ValueError:return None

def fetch_listing(client=requests):
    r=client.get("https://www.galdar.es/robots.txt",headers=HEADERS,timeout=12)
    if r.status_code!=200:raise RuntimeError(f"Galdar robots HTTP {r.status_code}")
    rp=RobotFileParser();rp.parse(r.text.splitlines())
    if not rp.can_fetch(AGENT,URL):raise PermissionError("Galdar disallows calendar")
    response=client.get(URL,headers=HEADERS,timeout=22,allow_redirects=False)
    response.raise_for_status()
    if len(response.content)>1_500_000:raise ValueError("Galdar response too large")
    return BeautifulSoup(response.content,"html.parser")

def extract(soup,today,places,norm,categorize):
    if "Gáldar" not in places:return []
    found=[]
    seen=set()
    for event in soup.select("div.eventon_list_event[itemtype*='Event']"):
        title_el=event.select_one(".evcal_event_title")
        a=event.select_one(".evo_event_schema a[itemprop='url'][href]")
        schema=event.select_one(".evo_event_schema")
        if not(title_el and a and schema):continue
        source_url=a["href"]
        url=urlsplit(source_url)
        if url.scheme!="https" or url.hostname!="www.galdar.es" or not url.path.startswith("/events/"):continue
        start_el=schema.select_one("meta[itemprop='startDate'][content]")
        end_el=schema.select_one("meta[itemprop='endDate'][content]")
        start=parse_schema_date(start_el.get("content") if start_el else "")
        end=parse_schema_date(end_el.get("content") if end_el else "")
        if not start:continue
        if end and end<start:continue
        end_day=(end or start).date()
        if end_day<today or start.date()>today+dt.timedelta(days=180):continue
        title=" ".join(title_el.get_text(" ",strip=True).split())[:180]
        if len(title)<5:continue
        key=(norm(title),start.date().isoformat())
        if key in seen:continue
        seen.add(key)
        place=schema.select_one("[itemprop='location'] [itemprop='name']")
        venue=" ".join(place.get_text(" ",strip=True).split())[:145] if place else ""
        if len(venue)<3:venue="Consultar el recinto en la ficha oficial"
        subtitle=event.select_one(".evcal_event_subtitle")
        detail=(" ".join(subtitle.get_text(" ",strip=True).split())[:220] if subtitle else
                "Evento de Cultura publicado por el Ayuntamiento de Gáldar. Consulta el detalle oficial.")
        if end and end.date()>start.date():
            start_value=start.date().isoformat()
            end_value=end.date().isoformat()
        else:
            start_value=start.isoformat(timespec="seconds")
            end_value=end.isoformat(timespec="seconds") if end and end>start else None
        found.append(dict(title=title,start=start_value,end=end_value,
             municipality="Gáldar",venue=venue,category=categorize(title),
             free=None,price="",details=detail,source_name=NAME,
             source_url=source_url,status="approved"))
    if not found:raise ValueError("Galdar calendar returned no future structured events")
    return found
