"""Read fresh date-verified activities from Ayuntamiento de Tejeda official agenda.

Unlike event-year handlists, this adapter discovers new posts on each daily
refresh. It checks official post publication dates, reads the main article,
validates explicit future day/month against publication year, and leaves
unknown event times, admission and venues unasserted.
"""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

NAME = "Ayuntamiento de Tejeda · agenda oficial"
BASE = "https://tejeda.eu"
LISTING = BASE + "/agenda-eventos/"
AGENT = "CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS = {"User-Agent": AGENT}
MONTHS = {"enero":1, "febrero":2, "marzo":3, "abril":4, "mayo":5,
          "junio":6, "julio":7, "agosto":8, "septiembre":9,
          "setiembre":9, "octubre":10, "noviembre":11, "diciembre":12}
MONTH_RX = "|".join(MONTHS)
DATE_RX = re.compile(r"(?<!\d)(\d{1,2})\s+de\s+("+MONTH_RX+
    r")(?:\s+de\s+(20\d{2}))?\b",re.I)
TIME_RX = re.compile(r"\b(?:a partir de las|de|a las|salida (?:a las |desde [^.]{0,80} a las ))"
    r"\s*(\d{1,2}):(\d{2})\s*(?:h(?:oras)?)?\b",re.I)
WEEKDAYS = {"lunes":0,"martes":1,"miercoles":2,"miércoles":2,
            "jueves":3,"viernes":4,"sabado":5,"sábado":5,
            "domingo":6}

def _html(client,url):
    resp=client.get(url,headers=HEADERS,timeout=20,allow_redirects=False)
    if resp.status_code!=200:raise RuntimeError("Tejeda HTTP "+str(resp.status_code))
    if len(resp.content)>1_600_000:raise ValueError("Tejeda response too large")
    return BeautifulSoup(resp.content,"html.parser")

def discover_cards(listing):
    urls={}
    for art in listing.select("article")[:30]:
        a=art.select_one("h4.brbl-post-title a[href]")
        if not a:continue
        title=" ".join(a.get_text(" ",strip=True).split())[:160]
        url=a.get("href","")
        parts=urlsplit(url)
        if parts.scheme!="https" or parts.hostname!="tejeda.eu" or not parts.path.endswith("/"):continue
        if not re.fullmatch(r"/[a-z0-9-]+/",parts.path):continue
        if len(title)<5:continue
        urls[url]=title
    if not urls:raise ValueError("Tejeda official agenda yielded no article links")
    return list(urls.items())[:14]

def _published(article):
    tag=article.select_one('meta[property="article:published_time"][content]')
    if not tag:return None
    try:return dt.date.fromisoformat(tag["content"][:10])
    except ValueError:return None

def _normalised_weekday(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD",text.lower())
        if unicodedata.category(c)!="Mn")

def _date_and_clock(text,published,today):
    candidates=[]
    for match in DATE_RX.finditer(text[:2200]):
        day=int(match.group(1))
        month=MONTHS[match.group(2).lower()]
        year=int(match.group(3)) if match.group(3) else published.year
        try:when=dt.date(year,month,day)
        except ValueError:continue
        if not(today<=when<=today+dt.timedelta(days=180)):continue
        if when<published-dt.timedelta(days=4):continue
        # A document for recurring activities may list several dates.
        # Do not silently select its first date as the only occurrence.
        candidates.append((match,when))
    if len(candidates)!=1:return None
    match,when=candidates[0]
    preceding=text[max(0,match.start()-24):match.start()]
    prior=_normalised_weekday(preceding)
    for name,value in WEEKDAYS.items():
        if re.search(r"\b"+_normalised_weekday(name)+r"\b",prior):
            if when.weekday()!=value:return None
            break
    # Don't scan later text such as phone office hours for an event start.
    context=text[match.end():match.end()+165]
    time_match=TIME_RX.search(context)
    if not time_match:return when.isoformat()
    hour,minute=int(time_match.group(1)),int(time_match.group(2))
    if hour>23 or minute>59:return when.isoformat()
    return when.isoformat()+f"T{hour:02d}:{minute:02d}:00"

def parse_article(soup,title,url,today,categorize):
    published=_published(soup)
    if not published or published<today-dt.timedelta(days=120):
        return None
    article=soup.select_one(".entry-content") or soup.select_one(".et_pb_post_content")
    if not article:return None
    text=" ".join(article.get_text(" ",strip=True).split())
    start=_date_and_clock(text,published,today)
    if start is None:return None
    lowered=text.casefold()
    venue="Consultar el recinto en la ficha oficial"
    if "club de pensionistas y simpatizantes" in lowered:
        venue="Club de Pensionistas y Simpatizantes Texeda"
    elif "plaza de ntra. sra. del socorro" in lowered:
        venue="Plaza de Nuestra Señora del Socorro"
    elif "gasolinera disa tejeda" in lowered:
        venue="Salida desde gasolinera DISA Tejeda"
    free=None
    if re.search(r"\bactividad\s+gratuita\b",lowered):
        free=1
    return dict(title=title,start=start,end=None,municipality="Tejeda",
                venue=venue,category=categorize(title),free=free,
                price="Gratis" if free==1 else "",
                details="Actividad de la agenda del Ayuntamiento de Tejeda. Consulta las condiciones de participación, inscripción y posibles cambios en el anuncio oficial.",
                source_name=NAME,source_url=url,status="approved")

def fetch_and_extract(today,places,categorize,client=requests):
    if "Tejeda" not in places:return []
    robot=client.get(BASE+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if robot.status_code!=200:raise RuntimeError("Tejeda robots HTTP "+str(robot.status_code))
    policy=RobotFileParser();policy.parse(robot.text.splitlines())
    if not policy.can_fetch(AGENT,LISTING):raise PermissionError("Tejeda disallows agenda")
    listing=_html(client,LISTING)
    events=[]
    for url,title in discover_cards(listing):
        if not policy.can_fetch(AGENT,url):continue
        try:
            page=_html(client,url)
            record=parse_article(page,title,url,today,categorize)
            if record:events.append(record)
        except (requests.exceptions.RequestException,RuntimeError,ValueError) as exc:
            # A single temporarily broken article does not block the others.
            print("WARN Tejeda agenda article:",url,str(exc)[:100])
    # Empty is legitimate for a town without newly scheduled events.
    return events
