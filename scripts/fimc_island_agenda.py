"""Single-festival, multi-island importer: 43rd FIMC 2027.

The public festival programme contains visits to eight islands. Each
individual show is accepted only if the original show's detail page
agrees with its source listing on island + day + starting hour and
provides a named physical venue. No festival-wide placeholder.
"""
from __future__ import annotations
import datetime as dt
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser
import venue_quality

INDEX="https://www.icdcultural.org/fimc/conciertos"
ROOT="https://www.icdcultural.org"
NAME="Festival Internacional de Música de Canarias · agenda oficial"
EVENT_PATH=r"/espectaculos-fimc-20\d{2}/[a-z0-9-]+"
INDEX_DATE=re.compile(r"^(\d{1,2})/(\d{1,2})/(20\d{2})\s+(\d{2}:\d{2})$")
VENUE_DATE=re.compile(r"^(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(20\d{2})\s*\|\s*(\d{2}:\d{2})$")
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT,"Accept":"text/html"}
MAX_DETAIL=24
GC_VENUES={
 "Auditorio Alfredo Kraus":"Las Palmas de Gran Canaria",
 "Teatro Guiniguada":"Las Palmas de Gran Canaria",
 "Teatro Pérez Galdós":"Las Palmas de Gran Canaria",
 "Teatro Cuyás":"Las Palmas de Gran Canaria",
 "Centro Cultural Guaires":"Gáldar",
 "Teatro Víctor Jara":"Santa Lucía de Tirajana",
 "Teatro Auditorio Agüimes":"Agüimes",
 "Teatro Cruce de Culturas":"Agüimes",
 "Teatro Juan Ramón Jiménez":"Telde",
 "Teatro Municipal Juan Ramón Jiménez":"Telde",
}
def official_link(url):
    try:
        part=urlsplit(url)
        return (part.scheme=="https" and part.hostname=="www.icdcultural.org"
                and part.port in (None,443) and not part.username and not part.password
                and not part.query and not part.fragment
                and bool(re.fullmatch(EVENT_PATH,part.path)))
    except (ValueError,TypeError):return False

def parse_day(text,pattern):
    match=pattern.fullmatch(" ".join(str(text).split()))
    if not match:return None
    try:
        day=dt.date(int(match.group(3)),int(match.group(2)),int(match.group(1)))
        hour=match.group(4)
        hh,mm=map(int,hour.split(":"))
        if hh>23 or mm>59:return None
        return day,hour
    except ValueError:return None

def listing(soup,today,island="Gran Canaria"):
    results=[]
    for block in soup.select(".div-block-252"):
        title_tag=block.select_one("h3.h3-nombre-artistas")
        link=next((a for a in block.select("a[href]") if
                   official_link(urljoin(ROOT,a.get("href","")))),None)
        if not title_tag or not link:continue
        title=" ".join(title_tag.get_text(" ",strip=True).split())
        for perf in block.select(".collection-item-30"):
            place=perf.select_one('[fs-cmsfilter-field="ISLA"]')
            date=perf.select_one('[fs-cmssort-type="date"]')
            if not place or " ".join(place.get_text(" ",strip=True).split())!=island:
                continue
            parsed=parse_day(date.get_text(" ",strip=True) if date else "",INDEX_DATE)
            if not parsed or not today<=parsed[0]<=today+dt.timedelta(days=180):
                continue
            results.append({"title":title,"url":urljoin(ROOT,link["href"]),
                            "date":parsed[0],"time":parsed[1],"island":island})
    return results

def detail_matches(soup,expected):
    # Cross-island extraction is supported by the source, but only an
    # island with a reviewed physical-venue/municipality map can publish.
    if expected["island"]!="Gran Canaria":
        return []
    matches=[]
    for show in soup.select(".collection-item-31"):
        place=show.select_one(".div-block-289 .sin-20")
        venue=show.select_one(".div-block-302 .nunito-32")
        date=show.select_one(".div-block-452")
        if not place or not venue or not date:continue
        island=" ".join(place.get_text(" ",strip=True).split())
        if island!=expected["island"]:continue
        parsed=parse_day(date.get_text(" ",strip=True),VENUE_DATE)
        if parsed!=(expected["date"],expected["time"]):continue
        venue_text=" ".join(venue.get_text(" ",strip=True).split())
        if not venue_quality.named_venue({
            "venue":venue_text,
            "municipality":GC_VENUES.get(venue_text,"Las Palmas de Gran Canaria")
        }):continue
        if expected["island"]=="Gran Canaria" and venue_text not in GC_VENUES:
            continue
        matches.append(venue_text)
    return matches

class Reader:
    def __init__(self,session=None):
        self.session=session or requests.Session()
        self.policy=None
    def read(self,url):
        if url!=INDEX and not official_link(url):
            raise ValueError("Festival page is not allowlisted")
        if self.policy is None:
            r=self.session.get(ROOT+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
            if r.status_code not in (200,404,410):
                raise RuntimeError("FIMC robots.txt unavailable")
            p=RobotFileParser()
            if r.status_code==200:p.parse(r.text.splitlines())
            else:p.allow_all=True
            self.policy=p
        if not self.policy.can_fetch(AGENT,url):
            raise PermissionError("Festival robots.txt disallows page")
        r=self.session.get(url,headers=HEADERS,timeout=20,allow_redirects=False)
        if r.status_code!=200 or len(r.content)>1_800_000:
            raise RuntimeError("Festival page unavailable")
        return BeautifulSoup(r.content,"html.parser")

def collect(today,*,reader=None,island="Gran Canaria"):
    reader=reader or Reader()
    rows=[]
    try:
        proposed=listing(reader.read(INDEX),today,island)
    except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
        return [],{"source":NAME,"found":0,"error":type(exc).__name__}
    unique_urls=list(dict.fromkeys(p["url"] for p in proposed))[:MAX_DETAIL]
    details={}
    errors=[]
    for url in unique_urls:
        try:details[url]=reader.read(url)
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
            errors.append(type(exc).__name__)
    seen=set()
    for entry in proposed:
        if entry["url"] not in details:continue
        for venue in detail_matches(details[entry["url"]],entry):
            key=(entry["url"],entry["date"],entry["time"],venue)
            if key in seen:continue
            seen.add(key)
            municipality=GC_VENUES.get(venue)
            if not municipality:continue
            rows.append({
                "title":entry["title"][:180],
                "start":entry["date"].isoformat()+"T"+entry["time"]+":00",
                "end":None,"municipality":municipality,
                "venue":venue,"category":"musica","free":None,"price":"",
                "details":"Festival Internacional de Música de Canarias · Fecha, isla y recinto contrastados.",
                "source_name":NAME,"source_url":entry["url"],"status":"approved"
            })
    return rows,{"source":NAME,"found":len(rows),"listing_candidates":len(proposed),
                 "detail_pages":len(details),"errors":errors[:5],
                 "error":"" if rows else "No independently verified performances"}
