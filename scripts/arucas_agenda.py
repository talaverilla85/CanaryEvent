"""Official Gran Canaria municipal event listing, conservative date parsing.

Arucas serves a public municipal page with event cards. Its robots.txt
responds HTTP 404 (missing policy), which is a robots-unavailable status,
not a denial. Explicit robots disallow/403/timeouts stop the source.
"""
from __future__ import annotations
import datetime as dt
import re
import requests
from urllib.parse import urljoin,urlsplit,parse_qs
from urllib.robotparser import RobotFileParser

NAME="Ayuntamiento de Arucas · agenda municipal"
URL="https://www.arucas.org/modules.php?file=eventos&mod=portal"
BASE="https://www.arucas.org/"
USER_AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":USER_AGENT}
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
        "noviembre":11,"diciembre":12}
MON="(?:"+"|".join(MONTHS)+")"
DAY_MONTH=re.compile(r"(\d{1,2})\s+de\s+("+MON+r")",re.I)
TWO_DAYS=re.compile(r"(\d{1,2})\s+y\s+(\d{1,2})\s+de\s+("+MON+r")",re.I)

def date_window(text,year):
    """Return known calendar date or period, never fabricated time of day."""
    t=" ".join(text.lower().split())
    year_match=re.search(r"\b(20\d{2})\b",t)
    if year_match:year=int(year_match.group(1))
    hits=list(DAY_MONTH.finditer(t))
    try:
        if len(hits)>=2:
            a,b=hits[0],hits[1]
            start=dt.date(year,MONTHS[a.group(2)],int(a.group(1)))
            end=dt.date(year,MONTHS[b.group(2)],int(b.group(1)))
            # A year transition is only permitted if the explicit end year
            # exists in the description; skip otherwise to avoid guessing.
            if end<start:return None
            return start,end
        both=TWO_DAYS.search(t)
        if both:
            mm=MONTHS[both.group(3)]
            return dt.date(year,mm,int(both.group(1))),dt.date(year,mm,int(both.group(2)))
        if len(hits)==1:
            h=hits[0];day=dt.date(year,MONTHS[h.group(2)],int(h.group(1)))
            return day,day
    except (ValueError,TypeError):
        return None
    return None

def fetch_listing(client=requests):
    robots=client.get(BASE+"robots.txt",headers=HEADERS,timeout=10,allow_redirects=False)
    if robots.status_code==200:
        p=RobotFileParser();p.parse(robots.text.splitlines())
        if not p.can_fetch(USER_AGENT,URL):raise PermissionError("Arucas robots disallow listing")
    elif robots.status_code not in (404,410):
        raise RuntimeError(f"Arucas robots unavailable or blocked: {robots.status_code}")
    r=client.get(URL,headers=HEADERS,timeout=22,allow_redirects=False)
    if r.status_code!=200:raise RuntimeError(f"Arucas agenda HTTP {r.status_code}")
    if len(r.content)>1_500_000:raise ValueError("Arucas response unexpectedly large")
    from bs4 import BeautifulSoup
    return BeautifulSoup(r.content,"html.parser")

def extract(soup,today,places,norm,categorize):
    if "Arucas" not in places:return []
    result=[]
    used=set()
    for art in soup.select("article"):
        title_tag=art.select_one(".entry-title")
        date_tag=art.select_one(".posted-on strong")
        a=art.select_one("a.image-post[href]")
        if not (title_tag and date_tag and a):continue
        title=" ".join(title_tag.get_text(" ",strip=True).split())[:170]
        dates=date_window(date_tag.get_text(" ",strip=True),today.year)
        if not dates or len(title)<5:continue
        start,end=dates
        if end<today or start>today+dt.timedelta(days=180):continue
        href=urljoin(BASE,a.get("href",""))
        u=urlsplit(href)
        q=parse_qs(u.query)
        if not(u.scheme=="https" and u.hostname=="www.arucas.org" and
               u.path.endswith("modules.php") and q.get("file")==["ver_gen"]
               and len(q.get("id",[]))==1):continue
        key=(norm(title),start.isoformat())
        if key in used:continue
        used.add(key)
        desc=art.select_one(".cat-links")
        details=(" ".join(desc.get_text(" ",strip=True).split())[:220] if desc else
                 "Actividad publicada por el Ayuntamiento de Arucas. Consulta el programa y el recinto en su ficha original.")
        result.append(dict(title=title,
             start=start.isoformat(),end=end.isoformat() if end>start else None,
             municipality="Arucas",venue="Consultar el recinto en la ficha oficial",
             category=categorize(title),free=None,price="",details=details,
             source_name=NAME,source_url=href,status="approved"))
    if not result:raise ValueError("Arucas listing returned no verifiable upcoming events")
    return result
