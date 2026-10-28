"""Three authoritative Gran Canaria cultural calendars (no generic aggregators).

Rechecked on each run.  We read only event facts and source URLs:
- Teatro Perez Galdos: explicit dated performances from its own detail pages
- LPA Cultura municipal calendar: event-specific listings with actual venue
- Sociedad Filarmonica: dated concerts and the named hall

No inferred recurrence, vague sites, generic programme pages, or cinema
multiplex schedules. A changed page is skipped rather than guessed.
"""
from __future__ import annotations
import datetime as dt
import re
import unicodedata
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import venue_quality

THEATRE_URL="https://teatroperezgaldos.es/"
THEATRE_NAME="Teatro Pérez Galdós · programación oficial"
LPA_URL="https://lpacultura.com/programs/actividades-culturales-2026"
LPA_NAME="LPA Cultura · agenda municipal oficial"
PHILHARMONIC_URL="https://sociedadfilarmonicalpgc.com/programacion/conciertos"
PHILHARMONIC_NAME="Sociedad Filarmónica de Las Palmas · conciertos"
MUNI="Las Palmas de Gran Canaria"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT,"Accept":"text/html"}
MAX_BYTES=1_300_000
MAX_DETAIL_PAGES=22
MON={"ENE":1,"FEB":2,"MAR":3,"ABR":4,"MAY":5,"JUN":6,
     "JUL":7,"AGO":8,"SEP":9,"OCT":10,"NOV":11,"DIC":12}
FULL_MON={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
          "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
THEATRE_DATE=re.compile(r"\b(?:[LMXJVSD])\s*(\d{1,2})\s+([A-Z]{3})\s+(20\d{2})\b")
FIL_DATE=re.compile(r"^(\d{1,2}) de ([a-záéíóú]+) (20\d{2})\s*-\s*(\d{2}:\d{2})h\.?$",re.I)
LPA_DATE=re.compile(r"^[A-Za-zÁÉÍÓÚáéíóú]{3}\.\s*(\d{1,2}),\s*([A-Za-zÁÉÍÓÚáéíóú]{3})\.(?:\s+de\s+(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}))?$",re.I)
CLOCK=re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
LPA_DATE_YEAR=2026

def norm(value):
    value=unicodedata.normalize("NFKD",str(value or "").casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())

def expected_url(url,base,path_pattern):
    try:
        parsed=urlsplit(url)
        origin=urlsplit(base)
        return bool(parsed.scheme=="https" and parsed.hostname==origin.hostname
            and parsed.port in (None,443) and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment and
            re.fullmatch(path_pattern,parsed.path))
    except (ValueError,TypeError):
        return False

def in_window(day,today):
    return today<=day<=today+dt.timedelta(days=180)

def formatted(entry):
    return " ".join(entry.get_text(" ",strip=True).split()) if entry else ""

def new_record(*,title,day,time="",venue,source,source_url,category,
               details="",free=None,price="",end=None):
    return dict(title=title[:180],
        start=day.isoformat()+("T"+time+":00" if time else ""),
        end=end,municipality=MUNI,venue=venue[:160],category=category,
        free=free,price=price,details=details[:320],source_name=source,
        source_url=source_url,status="approved")

class Reader:
    def __init__(self,session=None):
        self.session=session or requests.Session()
        self.robots={}
        self.checked=[]
    def html(self,url,base,path_regex):
        if not expected_url(url,base,path_regex):
            raise ValueError("Unexpected URL or domain in culture connector")
        parsed=urlsplit(url)
        host=parsed.hostname
        if host not in self.robots:
            robots=self.session.get(f"https://{host}/robots.txt",headers=HEADERS,
                                    timeout=12,allow_redirects=False)
            if robots.status_code not in (200,404,410):
                raise RuntimeError("Culture source robots unavailable")
            robot=RobotFileParser()
            if robots.status_code==200:robot.parse(robots.text.splitlines())
            else:robot.allow_all=True
            self.robots[host]=robot
        if not self.robots[host].can_fetch(AGENT,url):
            raise PermissionError("Culture source disallowed by robots")
        reply=self.session.get(url,headers=HEADERS,timeout=22,allow_redirects=False)
        if reply.status_code!=200:
            raise RuntimeError("Culture page not available")
        if (len(reply.content)>MAX_BYTES
            or "html" not in reply.headers.get("content-type","text/html").lower()):
            raise ValueError("Oversized or non-HTML culture page")
        self.checked.append(url)
        return BeautifulSoup(reply.content,"html.parser")

def theatre_day(text):
    match=THEATRE_DATE.search(norm(text).upper())
    if not match:return None
    try:return dt.date(int(match.group(3)),MON[match.group(2)],int(match.group(1)))
    except (KeyError,ValueError):return None

def theatre_sessions(soup,today):
    by_day={}
    for item in soup.select(".event-shows__item"):
        date=theatre_day(formatted(item.select_one("p.event-shows__date")))
        time=formatted(item.select_one("p.event-shows__time"))
        if not date or not in_window(date,today) or not CLOCK.fullmatch(time):
            continue
        by_day.setdefault(date,set()).add(time)
    return by_day

def extract_theatre(reader,today,categorize):
    soup=reader.html(THEATRE_URL,THEATRE_URL,r"/")
    rows=[]
    stats={"checked_pages":0,"skipped":0,"errored":[]}
    seen=set()
    for card in soup.select("article.event-card")[:MAX_DETAIL_PAGES]:
        link=card.select_one("a[href^='/evento/']")
        title=formatted(card.select_one("h2.event-card__title"))
        card_day=theatre_day(formatted(card.select_one("time.event-card__date")))
        if not link or len(title)<5 or not card_day or card_day>today+dt.timedelta(days=180):
            stats["skipped"]+=1
            continue
        url=urljoin(THEATRE_URL,link.get("href",""))
        if url in seen or not expected_url(url,THEATRE_URL,r"/evento/[a-z0-9-]+"):
            continue
        seen.add(url)
        try:
            detail=reader.html(url,THEATRE_URL,r"/evento/[a-z0-9-]+")
            stats["checked_pages"]+=1
            confirmed=formatted(detail.select_one("h2.page-header-event__title"))
            if norm(title)!=norm(confirmed):
                raise ValueError("Title does not match official event detail")
            sessions=theatre_sessions(detail,today)
            if not sessions:
                stats["skipped"]+=1
                continue
            subtitle=formatted(detail.select_one(".page-header-event__description"))
            for date,times in sorted(sessions.items()):
                if not in_window(date,today):continue
                sorted_times=sorted(times)
                # One row per event/day (database key is title + day). If
                # multiple shows, explicitly mention all printed showtimes.
                schedule=("Funciones: "+", ".join(sorted_times)+"."
                          if len(sorted_times)>1 else "")
                kind=("musica" if any(t in norm(title+" "+subtitle)
                      for t in ("concierto","musica","musical","opera"))
                      else "familia" if any(t in norm(title+" "+subtitle)
                      for t in ("familia","infantil","ninos")) else "cultura")
                rows.append(new_record(title=title,day=date,time=sorted_times[0],
                    venue="Teatro Pérez Galdós",source=THEATRE_NAME,source_url=url,
                    category=kind,details=(schedule+" Programación oficial del Teatro Pérez Galdós.").strip()))
        except (ValueError,PermissionError,RuntimeError,requests.RequestException) as err:
            stats["errored"].append({"event_url":url,"error_type":type(err).__name__})
    if not rows:raise RuntimeError("No dated Teatro Pérez Galdós sessions found")
    return rows,stats

def extract_philharmonic(soup,today):
    rows=[]
    for card in soup.select("a.card-article[href*='/programacion/conciertos/']"):
        u=urljoin(PHILHARMONIC_URL,card.get("href",""))
        if not expected_url(u,PHILHARMONIC_URL,
                            r"/programacion/conciertos/[a-z0-9-]+"):
            continue
        title=formatted(card.select_one("h2.card-article__title"))
        date_raw=formatted(card.select_one("time.card-article__date"))
        venue=formatted(card.select_one(".card-article__location"))
        match=FIL_DATE.fullmatch(date_raw)
        if not match or len(title)<7 or not venue_quality.named_venue(
              {"venue":venue,"municipality":MUNI}):
            continue
        month=FULL_MON.get(norm(match.group(2)))
        if not month:continue
        try:day=dt.date(int(match.group(3)),month,int(match.group(1)))
        except ValueError:continue
        if not in_window(day,today):continue
        rows.append(new_record(title=title,day=day,time=match.group(4),
              venue=venue,source=PHILHARMONIC_NAME,source_url=u,
              category="musica",
              details="Concierto de la Sociedad Filarmónica de Las Palmas de Gran Canaria."))
    return rows

def extract_lpa(soup,today,categorize):
    rows=[]
    for card in soup.select("div.show-event"):
        link=card.select_one(".name a[href]")
        if not link:continue
        url=link.get("href","")
        if not expected_url(url,LPA_URL,r"/events/[a-z0-9-]+"):
            continue
        title=formatted(link)
        schedule=formatted(card.select_one(".mt-2 .pl-2"))
        match=LPA_DATE.fullmatch(schedule)
        location_boxes=[formatted(e) for e in card.select(".mt-1 .pl-2")]
        if len(title)<6 or not match or not location_boxes:continue
        venue=location_boxes[0][:160]
        # A walking itinerary/various stops has no single venue for maps.
        if any(x in norm(venue) for x in (
           "recorrido","varias ubicaciones","diversos espacios","itinerante")):
            continue
        if not venue_quality.named_venue({"venue":venue,"municipality":MUNI}):continue
        month=MON.get(norm(match.group(2)).upper())
        if not month:continue
        try:day=dt.date(LPA_DATE_YEAR,month,int(match.group(1)))
        except ValueError:continue
        if not in_window(day,today):continue
        pricing=location_boxes[1].strip().strip(".") if len(location_boxes)>1 else ""
        free=1 if norm(pricing) in ("gratuito","gratis","entrada libre") else None
        price="Gratis" if free==1 else pricing if re.fullmatch(
            r"\d{1,4}(?:[,.]\d\d)?\s*€",pricing) else ""
        category_text=norm(" ".join(formatted(e) for e in card.select(
            ".p-2 .rounded-lg")))
        kind=("musica" if any(t in category_text for t in
              ("musica","folclore")) else "familia"
              if "infantil" in category_text else "cultura"
              if any(t in category_text for t in
              ("teatro","cine","danza","multidisciplinar")) else categorize(title))
        rows.append(new_record(title=title,day=day,time=match.group(3) or "",
            venue=venue,source=LPA_NAME,source_url=url,category=kind,
            price=price,free=free,details="Actividad cultural del Ayuntamiento de Las Palmas de Gran Canaria."))
    return rows

def collect(today,*,reader=None,categorize=None):
    reader=reader or Reader()
    categorize=categorize or (lambda title:"cultura")
    sources=[]
    outputs=[]
    for name,url,path,extractor in (
        (LPA_NAME,LPA_URL,r"/programs/actividades-culturales-2026",lambda soup:extract_lpa(soup,today,categorize)),
        (PHILHARMONIC_NAME,PHILHARMONIC_URL,r"/programacion/conciertos",lambda soup:extract_philharmonic(soup,today)),
    ):
        try:
            source=reader.html(url,url,path)
            records=extractor(source)
            if not records:raise ValueError("Source returned no individually dated events")
            outputs.extend(records)
            sources.append({"name":name,"found":len(records),"error":""})
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as error:
            sources.append({"name":name,"found":0,"error":type(error).__name__})
    try:
        records,extra=extract_theatre(reader,today,categorize)
        outputs.extend(records)
        sources.append({"name":THEATRE_NAME,"found":len(records),
                        "detail_pages":extra["checked_pages"],
                        "skipped":extra["skipped"],
                        "errors":extra["errored"][:6],
                        "error":""})
    except (ValueError,RuntimeError,PermissionError,requests.RequestException) as error:
        sources.append({"name":THEATRE_NAME,"found":0,"error":type(error).__name__})
    return outputs,sources
