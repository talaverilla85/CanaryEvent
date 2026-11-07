"""Direct, verified performances from Teatro Cuyás and Sala Insular de Teatro.

These two institutional venues publish a human-readable agenda with a
separate row for each session. Do not infer performances from programme
brochures or poster dates; preserve both date and exact starting clock.
Historical/marketing entries and unnamed locations are excluded.
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

SOURCES=(
 {"name":"Teatro Cuyás · agenda oficial","site":"https://teatrocuyas.com",
  "url":"https://teatrocuyas.com/programacion/","venue":"Teatro Cuyás"},
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

# WordPress/Elementor programme used by Teatro Cuyás since November 2026.
# Sala Insular de Teatro still uses the older .agenda_evento markup.
WP_DETAIL=r"/espectaculo/[a-z0-9-]+/"
WP_IMAGE=r"/wp-content/uploads/[0-9]{4}/[0-9]{2}/[a-zA-Z0-9._%-]+\.(?:jpg|jpeg|png|webp|avif)"
WP_DATE=re.compile(r"(?<!\d)([0-3]?\d)/([01]?\d)(?!\d)")
WP_TIME=re.compile(r"(?<!\d)((?:[01]?\d|2[0-3]):[0-5]\d)(?!\d)")
WEEKDAYS={"lun":0,"mar":1,"mie":2,"jue":3,"vie":4,"sab":5,"dom":6}

def normalized(value):
    text=unicodedata.normalize("NFKD",str(value or "").casefold())
    return "".join(c for c in text if not unicodedata.combining(c))

def wp_session_day(day,month,weekday,today):
    """Dates on the new cards omit the year: accept only a corroborated
    weekday and the unique date in the next 180 days; never guess otherwise."""
    week=WEEKDAYS.get(normalized(weekday).strip()[:3])
    if week is None:return None
    candidates=[]
    for year in (today.year,today.year+1):
        try:date=dt.date(year,month,day)
        except ValueError:continue
        if today<=date<=today+dt.timedelta(days=180) and date.weekday()==week:
            candidates.append(date)
    return candidates[0] if len(candidates)==1 else None

def wp_image(card,site):
    node=card.select_one(".cy-tarjeta__imagen img[src]")
    if not node:return ""
    url=urljoin(site+"/",node.get("src",""))
    return url if expected_url(url,site,WP_IMAGE) and len(url)<750 else ""

def extract_wordpress(soup,source,today):
    records=[]
    checked=skipped=0
    for card in soup.select(".cy-tarjeta"):
        checked+=1
        # The category is in the official WordPress post's class list:
        # never advertise a different room as Teatro Cuyás.
        ancestor=card.find_parent(class_=re.compile(r"\be-loop-item\b"))
        css=ancestor.get("class",[]) if ancestor else []
        hall="sala-"+("teatro-cuyas" if source["venue"]=="Teatro Cuyás" else "sala-insular-de-teatro")
        title_el=card.select_one(".cy-tarjeta__titulo a[href]")
        title=" ".join(title_el.get_text(" ",strip=True).split()) if title_el else ""
        url=urljoin(source["site"]+"/",title_el.get("href","")) if title_el else ""
        if (hall not in css or len(title)<6
            or not expected_url(url,source["site"],WP_DETAIL)
            or "venta de entradas" in title.casefold()):
            skipped+=1
            continue
        sessions={}
        for li in card.select(".cuyas-mini-funciones li"):
            spans=li.find_all("span",recursive=False)
            if len(spans)<2:continue
            raw=" ".join(spans[0].get_text(" ",strip=True).split())
            match=WP_DATE.search(raw)
            time=WP_TIME.search(spans[1].get_text(" ",strip=True))
            if not match or not time:continue
            weekday=raw[:match.start()].strip()
            day=wp_session_day(int(match.group(1)),int(match.group(2)),weekday,today)
            if day:
                sessions.setdefault(day,set()).add(time.group(1).zfill(5))
        if not sessions:
            skipped+=1
            continue
        image=wp_image(card,source["site"])
        kind=("musica" if "genero-musica" in css else "cultura")
        for day,times in sorted(sessions.items()):
            seq=sorted(times)
            details="Funciones: "+", ".join(seq) if len(seq)>1 else ""
            records.append({"title":title[:180],"start":day.isoformat()+"T"+seq[0]+":00",
                "end":None,"municipality":MUNI,"venue":source["venue"],
                "category":kind,"free":None,"price":"",
                "details":details,"source_name":source["name"],
                "source_url":url,"status":"approved",
                "image_url":image,"image_alt":title[:180] if image else "",
                "image_origin":source["name"] if image else "",
                "image_status":"official_remote" if image else "not_available"})
    return records,{"cards_checked":checked,"cards_skipped":skipped,
                    "performances":len(records)}

def extract(soup,source,today):
    if source["site"]=="https://teatrocuyas.com" and soup.select(".cy-tarjeta"):
        return extract_wordpress(soup,source,today)
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
