"""Official Santa Brígida municipal events from Tribe Events JSON-LD calendars.

Read only the current and following month's public calendar. Event periods
remain periods; never convert a multiday activity into fictitious daily shows.
"""
import datetime as dt,json,html,time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

NAME="Ayuntamiento de Santa Brígida · agenda de eventos"
BASE="https://eventos.santabrigida.es"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT}
def month_urls(today):
    a=today.year*12+today.month-1
    months=[(a+i)//12 for i in range(2)]
    return [f"{BASE}/eventos/mes/{(a+i)//12:04d}-{(a+i)%12+1:02d}/" for i in range(2)]
def polite_get(client,url,timeout):
    """Retry a transient network error once; never retry an explicit block."""
    for attempt in range(2):
        try:
            return client.get(url,headers=HEADERS,timeout=timeout,
                              allow_redirects=False)
        except (requests.exceptions.Timeout,requests.exceptions.ConnectionError):
            if attempt:raise
            time.sleep(0.6)

def check_robots(client=requests):
    r=polite_get(client,BASE+"/robots.txt",18)
    if r.status_code!=200:raise RuntimeError("Santa Brígida robots unavailable HTTP "+str(r.status_code))
    p=RobotFileParser();p.parse(r.text.splitlines())
    for u in month_urls(dt.date.today()):
        if not p.can_fetch(AGENT,u):raise PermissionError("Santa Brígida disallows event calendar")
def fetch_month(client,url):
    r=polite_get(client,url,25)
    if r.status_code!=200:raise RuntimeError(f"Santa Brígida calendar HTTP {r.status_code}")
    if len(r.content)>2_000_000:raise ValueError("Santa Brígida calendar response too large")
    return BeautifulSoup(r.content,"html.parser")
def parse_iso(text):
    try:return dt.datetime.fromisoformat(text)
    except (TypeError,ValueError):return None
def extract_pages(soups,today,places,categorize):
    if "Santa Brígida" not in places:return []
    events={}
    for soup in soups:
        for script in soup.select('script[type="application/ld+json"]')[:5]:
            try:data=json.loads(script.string or script.get_text())
            except (TypeError,ValueError):continue
            if isinstance(data,dict):data=[data]
            if not isinstance(data,list):continue
            for event in data[:160]:
                if not isinstance(event,dict) or event.get("@type")!="Event":continue
                status=str(event.get("eventStatus") or "")
                if status and "EventScheduled" not in status:continue
                u=str(event.get("url") or "")
                p=urlsplit(u)
                if p.scheme!="https" or p.hostname!="eventos.santabrigida.es" or not p.path.startswith("/eventos/"):continue
                start=parse_iso(event.get("startDate"))
                end=parse_iso(event.get("endDate")) or start
                if not start or not end or end.date()<start.date():continue
                if end.date()<today or start.date()>today+dt.timedelta(days=180):continue
                title=html.unescape(str(event.get("name") or "")).strip()[:170]
                if len(title)<5:continue
                loc=event.get("location") or {}
                if not isinstance(loc,dict):loc={}
                venue=html.unescape(str(loc.get("name") or "")).strip()[:145]
                if len(venue)<4:venue="Consultar el recinto en la ficha oficial"
                # The publisher exposes some synthetic 05:00 times for workshops.
                # Treat ALL multiday programs as periods; one-day events with
                # suspicious overnight hour become date-only.
                multiday=end.date()!=start.date()
                has_time=(8<=start.hour<24 and not multiday)
                start_value=start.strftime("%Y-%m-%dT%H:%M:%S") if has_time else start.date().isoformat()
                end_value=(end.strftime("%Y-%m-%dT%H:%M:%S") if has_time and end>start
                           else end.date().isoformat() if multiday else None)
                events[u]=dict(title=title,start=start_value,end=end_value,
                      municipality="Santa Brígida",venue=venue,category=categorize(title),
                      free=None,price="",details="Actividad publicada en la agenda municipal de Santa Brígida. Verifica los detalles y, si es un programa de varias jornadas, los días concretos en la fuente oficial.",
                      source_name=NAME,source_url=u,status="approved")
    if not events:raise ValueError("Santa Brígida calendars contain no verifiable future events")
    return list(events.values())
def article_description(soup):
    """Readable excerpts from the actual event, never WordPress 'Read more' HTML.

    Prefer useful information on access/booking to long promotional prose.
    No HTML is copied into JSON; this is a bounded editorial excerpt.
    """
    section=soup.select_one(".tribe-events-single-event-description")
    if section is None:
        return ""
    paragraphs=[]
    for tag in section.select("p, li"):
        text=" ".join(tag.get_text(" ",strip=True).split())
        if len(text)>=15 and text not in paragraphs:
            paragraphs.append(text)
    if not paragraphs:
        return ""
    lead=" ".join(paragraphs[:2])
    if len(lead)>650:
        lead=lead[:650].rsplit(" ",1)[0].rstrip(" ,;:")
        if not lead.endswith((".","!","?")):
            lead+="…"
    priority=[]
    for text in paragraphs[2:]:
        if any(word in text.casefold() for word in (
                "precio","inscrip","reserva","plazas","gratis","gratuit",
                "dirigid","acceso","edad","informaci","contacto","aforo")):
            priority.append(text[:240])
        if len(priority)==3:
            break
    return " ".join([lead]+priority)[:1450]


def enrich_event_articles(rows,rp,client):
    """Read linked municipal articles after robots permission. Fail safe per item."""
    for event in rows[:25]:
        url=event["source_url"]
        parts=urlsplit(url)
        if (parts.scheme!="https" or parts.hostname!="eventos.santabrigida.es"
                or not parts.path.startswith("/eventos/")
                or not rp.can_fetch(AGENT,url)):
            continue
        try:
            response=polite_get(client,url,18)
            if response.status_code!=200 or len(response.content)>1_500_000:
                continue
            description=article_description(BeautifulSoup(response.content,"html.parser"))
            if description:
                event["details"]=description
        except (requests.RequestException,ValueError,TypeError):
            # Keep the qualified calendar event rather than publish a teaser.
            pass
    return rows


def fetch_and_extract(today,places,categorize,client=requests):
    # Consistent robots policy for the exact two calendar paths.
    robots=polite_get(client,BASE+"/robots.txt",18)
    if robots.status_code!=200:raise RuntimeError(f"Santa Brígida robots HTTP {robots.status_code}")
    rp=RobotFileParser();rp.parse(robots.text.splitlines())
    urls=month_urls(today)
    if any(not rp.can_fetch(AGENT,u) for u in urls):raise PermissionError("Santa Brígida calendars disallowed")
    soups=[fetch_month(client,u) for u in urls]
    rows=extract_pages(soups,today,places,categorize)
    return enrich_event_articles(rows,rp,client)
