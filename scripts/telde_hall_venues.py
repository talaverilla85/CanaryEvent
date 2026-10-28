"""Recover venue from dated, linked events on Telde Cultura's own hall calendar.

An "Organiza" field on an event page is NOT standalone venue evidence.
Instead match an official event URL AND its exact date/time on the
specific venue's own dated programme, under a strict trusted domain.
No guessing and no automatic geocoding.
"""
from __future__ import annotations
import datetime as dt
import re
import unicodedata
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import venue_quality

NAME="Telde Cultura · funciones vinculadas a recintos oficiales"
HOST="teldecultura.org"
HALL="Teatro Municipal Juan Ramón Jiménez"
HALL_URL="https://teldecultura.org/areas/teatro-municipal-juan-ramon-jimenez/"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT,"Accept":"text/html"}
MAX_PAGES=5
DATE_RE=re.compile(r"^(\d{2})/(\d{2})/(20\d{2})$")
TIME_RE=re.compile(r"^([01]\d|2[0-3]):[0-5]\d")

def event_url(url):
    try:
        u=urlsplit(str(url or ""))
        return bool(u.scheme=="https" and u.hostname==HOST and u.port in (None,443)
                    and not u.username and not u.password and not u.query and not u.fragment
                    and re.fullmatch(r"/events/[a-z0-9-]+/",u.path))
    except (ValueError,TypeError):
        return False

def norm(text):
    s=unicodedata.normalize("NFKD",str(text or "").casefold())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())

def parse_hall(soup,today):
    """Return only unique official event URL/date/time combinations."""
    found={}
    for card in soup.select("div.bloque-evento"):
        title=card.select_one("h4.em-item-title a[href]")
        day=card.select_one(".fechas-tarjeta")
        hour=card.select_one(".em-event-time")
        if not title or not day or not hour or not event_url(title.get("href","")):
            continue
        dm=DATE_RE.fullmatch(day.get_text(" ",strip=True))
        hm=TIME_RE.match(hour.get_text(" ",strip=True))
        if not dm or not hm:
            continue
        try: date=dt.date(int(dm.group(3)),int(dm.group(2)),int(dm.group(1)))
        except ValueError:continue
        if date<today or date>today+dt.timedelta(days=180):
            continue
        href=title["href"]
        key=(href,date.isoformat())
        entry=(norm(title.get_text(" ",strip=True)),hm.group(0))
        if key in found and found[key]!=entry:
            found[key]=None    # Conflicting showtimes, never silently guess
        elif key not in found:
            found[key]=entry
    return found

def hall_evidence(entries,event):
    url=event.get("organizer_url")
    if not event_url(url) or event.get("municipality")!="Telde":
        return ""
    key=(url,str(event.get("start",""))[:10])
    recorded=entries.get(key)
    if not recorded:
        return ""
    actual_title,actual_hour=recorded
    if norm(event.get("title"))!=actual_title:
        return ""
    start=str(event.get("start") or "")
    if len(start)>=16 and actual_hour!=start[11:16]:
        return ""
    return HALL

def _pages(client,max_pages=MAX_PAGES):
    r=client.get("https://"+HOST+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if r.status_code not in (200,404,410):
        raise RuntimeError("Telde Cultura robots unavailable")
    rp=RobotFileParser()
    if r.status_code==200:rp.parse(r.text.splitlines())
    else:rp.allow_all=True
    for num in range(1,max_pages+1):
        url=HALL_URL if num==1 else HALL_URL+"?pno="+str(num)
        if not rp.can_fetch(AGENT,url):
            raise PermissionError("Telde Cultura robots disallow hall programme")
        response=client.get(url,headers=HEADERS,timeout=20,allow_redirects=False)
        if response.status_code!=200 or len(response.content)>1_400_000:
            raise RuntimeError("Telde Cultura hall programme unavailable")
        if "text/html" not in response.headers.get("content-type","text/html"):
            raise ValueError("Unexpected Telde Cultura hall format")
        yield BeautifulSoup(response.content,"html.parser")

def enrich(conn,now,today,*,client=None,max_pages=MAX_PAGES):
    records=[dict(row) for row in conn.execute(
        """SELECT id,title,start,municipality,venue,organizer_url
           FROM events WHERE status='approved' AND
           substr(COALESCE("end",start),1,10)>=? AND municipality='Telde'""",
        (today.isoformat(),))]
    targets=[x for x in records if not venue_quality.named_venue(x)
             and event_url(x["organizer_url"])]
    report={"source":NAME,"checked_at":now,"found":0,"added":0,"changed":0,
            "eligible":len(targets),"error":""}
    if not targets:return report
    client=client or requests.Session()
    entries={}
    try:
        for soup in _pages(client,max_pages):
            entries.update(parse_hall(soup,today))
            report["found"]+=1
    except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
        # A partial crawl can be useful, but never claim a successful sync.
        report["error"]=type(exc).__name__
    for event in targets:
        place=hall_evidence(entries,event)
        if place and venue_quality.named_venue({"venue":place,"municipality":"Telde"}):
            conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                         (place,now,event["id"]))
            report["changed"]+=1
    conn.commit()
    return report
