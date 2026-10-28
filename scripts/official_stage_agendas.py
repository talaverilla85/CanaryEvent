"""Direct, verified performances from Teatro Cuyás and Sala Insular de Teatro.

These two institutional venues publish a human-readable agenda with a
separate row for each session. Do not infer performances from programme
brochures or poster dates; preserve both date and exact starting clock.
Historical/marketing entries and unnamed locations are excluded.
"""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import venue_quality

SOURCES=(
 {"name":"Teatro Cuyás · agenda oficial","site":"https://teatrocuyas.com",
  "url":"https://teatrocuyas.com/agenda.html","venue":"Teatro Cuyás"},
 {"name":"Sala Insular de Teatro · agenda oficial","site":"https://salainsulardeteatro.com",
  "url":"https://salainsulardeteatro.com/agenda.html","venue":"Sala Insular de Teatro"},
)
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
DATE=re.compile(r"([0-3]?\d)/([01]?\d)/(20\d{2})")
CLOCK=re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DETAIL_LINK=re.compile(r"/evento-\d+-[a-z0-9-]+\.html")
MUNI="Las Palmas de Gran Canaria"

def expected_url(url,base,path_pattern):
    try:
        p=urlsplit(url);b=urlsplit(base)
        return bool(p.scheme=="https" and p.hostname==b.hostname
            and p.port in (None,443) and not p.username and not p.password
            and not p.query and not p.fragment
            and re.fullmatch(path_pattern,p.path))
    except (ValueError,TypeError):return False

def extract(soup,source,today):
    records=[]
    checked=skipped=0
    for card in soup.select(".agenda_evento"):
        checked+=1
        title=" ".join((card.select_one(".agenda_tituloevento") or BeautifulSoup("","html.parser")).get_text(" ",strip=True).split())
        actual=(card.select_one(".calendar_zonaevento b"))
        venue=" ".join(actual.get_text(" ",strip=True).split()) if actual else ""
        link=card.select_one("a[href^='evento-']")
        url=urljoin(source["site"]+"/",link.get("href","")) if link else ""
        parsed=urlsplit(url)
        if (len(title)<6 or not venue or venue.casefold()!=source["venue"].casefold()
            or "venta de entradas" in title.casefold()
            or not expected_url(url,source["site"],DETAIL_LINK.pattern)
            or not venue_quality.named_venue({"venue":venue,"municipality":MUNI})):
            skipped+=1
            continue
        sessions={}
        for tr in card.select("table.mtable tr"):
            cells=tr.find_all("td",recursive=False)
            if len(cells)<2:continue
            found=DATE.search(cells[0].get_text(" ",strip=True))
            time=" ".join(cells[1].get_text(" ",strip=True).split())
            if not found or not CLOCK.fullmatch(time):continue
            try:day=dt.date(int(found.group(3)),int(found.group(2)),int(found.group(1)))
            except ValueError:continue
            if not today<=day<=today+dt.timedelta(days=180):continue
            sessions.setdefault(day,set()).add(time)
        for day,times in sorted(sessions.items()):
            seq=sorted(times)
            detail="Funciones: "+", ".join(seq) if len(seq)>1 else ""
            kind=("musica" if any(x in title.casefold() for x in
                ("jazz","concierto","big band","musical","música","festival fex"))
                else "cultura")
            records.append({"title":title[:180],"start":day.isoformat()+"T"+seq[0]+":00",
                            "end":None,"municipality":MUNI,"venue":venue,
                            "category":kind,"free":None,"price":"",
                            "details":detail,"source_name":source["name"],
                            "source_url":url,"status":"approved"})
    return records,{"cards_checked":checked,"cards_skipped":skipped,
                    "performances":len(records)}

def download(source,session=None):
    sess=session or requests.Session()
    host=urlsplit(source["site"]).hostname
    headers={"User-Agent":AGENT,"Accept":"text/html"}
    r=sess.get(source["site"]+"/robots.txt",timeout=12,headers=headers,allow_redirects=False)
    if r.status_code not in (200,404,410):
        raise RuntimeError("Official venue robots.txt is unavailable")
    rp=RobotFileParser()
    if r.status_code==200:rp.parse(r.text.splitlines())
    else:rp.allow_all=True
    if not rp.can_fetch(AGENT,source["url"]):
        raise PermissionError("Official venue robots.txt disallows this agenda")
    response=sess.get(source["url"],timeout=24,headers=headers,allow_redirects=False)
    if response.status_code!=200:raise RuntimeError("Official venue agenda unavailable")
    if len(response.content)>1_600_000 or "html" not in response.headers.get("Content-Type","text/html").lower():
        raise ValueError("Oversized or non-HTML venue agenda")
    return BeautifulSoup(response.content,"html.parser")

def collect(today,*,fetch=download):
    all_rows=[]
    outcomes=[]
    for source in SOURCES:
        try:
            rows,stats=extract(fetch(source),source,today)
            if not rows:raise ValueError("No individually dated upcoming performances found")
            all_rows.extend(rows)
            outcomes.append({"source":source["name"],"found":len(rows),
                             "error":"","stats":stats})
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
            outcomes.append({"source":source["name"],"found":0,
                             "error":type(exc).__name__})
    return all_rows,outcomes
