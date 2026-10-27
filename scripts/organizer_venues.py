"""Secondary venue verification from the exact official organizer event page.

Limited to explicit, approved hostnames: no arbitrary URLs, redirects, private
IP probes, commercial aggregator scraping or copied event descriptions.
Only verified factual venue names enter the existing SQLite event record.
"""
from __future__ import annotations
import datetime as dt
import difflib
import json
import re
import sqlite3
import time
import unicodedata
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import venue_facts
import venue_quality
import structured_organizer_venues

NAME="Recintos · fichas oficiales de organizadores"
USER_AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":USER_AGENT,"Accept":"text/html"}
# Exact domains, not arbitrary subdomains or similar-looking web addresses.
HOSTS={
    "teldecultura.org", "lpacultura.com", "lpabibliotecas.com",
    "actividadesjuventud.laspalmasgc.es", "ingenio.es", "eventos.santabrigida.es",
    "arucas.org", "salainsulardeteatro.com", "cultura.icdcultural.org",
    "galdar.es", "teatroguiniguada.es",
    "ofgrancanaria.com", "casafrica.es",
}
MAX_PAGES=24
CACHE_DAYS=5
PARSER_VERSION='structured-venues-2026-10-27-v2'
LABEL=re.compile(
    r"(?<!\w)(?:Lugar|Localizaci[oó]n|Ubicaci[oó]n|Recinto)\s*:?\s*"
    r"((?:biblioteca|casa|centro|teatro|museo|sala|auditorio|cine|"
    r"pabell[oó]n|plaza|estadio|recinto|polideportivo|espacio|"
    r"la\s+grada|yelmo\s+cine)\b[^\n\r.!?]{3,120})",re.I)
TRAILING=re.compile(
    r"\s+(?:Precio|Fecha|Fechas del evento|Cu[aá]ndo|Disponibilidad|"
    r"Servicios|Organiza|Horario|Informaci[oó]n|Inscripciones|"
    r"Other Events|Adquirir|Contacto|c/|Calle)\b",re.I)
BLOCK=re.compile(r"\b(?:itinerante|recorrido|varias sedes|distintos recintos|varias ubicaciones)\b",re.I)

def normalize(s):
    t=unicodedata.normalize("NFKD",unicodedata.normalize("NFKC",str(s or "")).lower())
    return re.sub(r"[^a-z0-9]+"," ","".join(c for c in t if not unicodedata.combining(c))).strip()

def valid_url(url):
    if not isinstance(url,str) or len(url)>550:return ""
    try:
        p=urlsplit(url)
        if p.scheme!="https" or not p.hostname or p.port not in (None,443) or p.username or p.password:return ""
        hostname=p.hostname.lower()
        if hostname.startswith("www."):hostname=hostname[4:]
        if hostname not in HOSTS:return ""
        if not p.path or p.path=="/":return ""
        # Generic agenda pages are not evidence of a particular event.
        if p.path.rstrip("/") in ("/agenda","/events","/eventos","/programacion","/programacion-guiniguada"):return ""
        return url
    except ValueError:return ""

def _similar_title(a,b):
    a,b=normalize(a),normalize(b)
    if not a or not b:return False
    return a==b or (len(a)>=12 and a in b) or (len(b)>=12 and b in a) or difflib.SequenceMatcher(a=a,b=b).ratio()>=0.72

def title_matches(soup,title):
    expected=normalize(title)
    if not expected:return False
    labels=[]
    for css in ('h1','meta[property="og:title"]','title','h2.entry-title'):
        for el in soup.select(css)[:3]:
            labels.append(str(el.get("content") or el.get_text(" ",strip=True)))
    for label in labels:
        actual=normalize(label)
        if not actual:continue
        if _similar_title(expected,actual):return True
    return False

def _organizer_event_schema(soup):
    for el in soup.select('script[type="application/ld+json"]')[:9]:
        try:obj=json.loads(el.string or el.get_text())
        except (ValueError,TypeError):continue
        stack=[obj]
        while stack:
            node=stack.pop()
            if isinstance(node,list):stack.extend(node)
            if not isinstance(node,dict):continue
            kind=node.get("@type",[])
            if isinstance(kind,str):kind=[kind]
            if any(x=="Event" or str(x).endswith("/Event") for x in kind):return node
            if isinstance(node.get("@graph"),list):stack.extend(node["@graph"])
    return {}

def _named(raw,municipality):
    candidate=" ".join(str(raw or "").split())[:120]
    if candidate.casefold() in ("gran canaria","las palmas","canarias"):return ""
    e={"venue":candidate,"municipality":municipality}
    if not venue_quality.named_venue(e):return ""
    if any(word in normalize(candidate) for word in ("organiza","universidad popular")) and len(candidate)>90:return ""
    return candidate

def parse_official(soup,title,municipality):
    """A title match and a named location in the event's content are required."""
    if not title_matches(soup,title):return ""
    schema=_organizer_event_schema(soup)
    if schema.get("name") and not _similar_title(schema["name"],title):
        schema={}
    loc=schema.get("location")
    if isinstance(loc,list):
        if len(loc)!=1:return ""
        loc=loc[0]
    if isinstance(loc,dict):
        name=_named(loc.get("name"),municipality)
        if name:return name
    for css in ('[itemprop="location"] [itemprop="name"]',
                '.mec-event-loc-place','.tribe-venue',
                '.tribe-events-venue-details','.event-location'):
        node=soup.select_one(css)
        if node:
            name=_named(node.get_text(" ",strip=True),municipality)
            if name:return name
    node=(soup.select_one('.description') or
          soup.select_one('.entry-content') or soup.select_one('article') or
          soup.select_one('main') or soup.select_one('body'))
    if not node:return ""
    content=node.get_text(" ",strip=True)[:12000]
    # A programme may describe an itinerant *performance* while still
    # publishing one concrete official venue; a strong Lugar label wins.
    # Without such an explicit label do not choose a random stop on a route.
    # Organizers often use a stand-alone "Lugar Biblioteca..." field with
    # no colon. Read that label, not an arbitrary nearby organization name.
    matches=[]
    for match in LABEL.finditer(unicodedata.normalize("NFKC",content)):
        fragment=TRAILING.split(match.group(1),1)[0]
        fragment=re.split(r"\s+[|•]\s+|https?://|,\s*[Cc]\/",fragment,1)[0]
        fragment=re.split(r"\s+c/\s+|,\s*c/",fragment,1,flags=re.I)[0]
        fragment=re.split(r"\s+\(",fragment,1)[0]
        fragment=fragment.strip(" -:;.,()«»“”")
        named=venue_facts._clean(fragment,municipality)
        if named:matches.append(named)
        elif normalize(fragment).startswith(("la grada","yelmo cine")):
            valid=fragment[:85].strip()
            if _named(valid,municipality):matches.append(valid)
    if matches:
        distinct={normalize(x):x for x in matches}
        return next(iter(distinct.values())) if len(distinct)==1 else ""
    if BLOCK.search(content):return ""
    return venue_facts.from_description(content,municipality)

def _robots(client,host,cache,url):
    if host not in cache:
        r=client.get("https://"+host+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
        if r.status_code in (404,410):cache[host]=None
        elif r.status_code==200:
            parser=RobotFileParser();parser.parse(r.text.splitlines())
            cache[host]=parser
        else:raise RuntimeError("organizer robots unavailable: "+str(r.status_code))
    policy=cache[host]
    return policy is None or policy.can_fetch(USER_AGENT,url)

def _same_official_redirect(client,url,response,robots_cache):
    """Follow a single HTTPS redirect within the exact allowed organizer host."""
    if response.status_code not in (301,302,307,308):
        return response
    target=urljoin(url,response.headers.get("Location",""))
    initial=urlsplit(url).hostname or ""
    final=urlsplit(target).hostname or ""
    if (not valid_url(target) or
        initial.removeprefix("www.").lower()!=final.removeprefix("www.").lower() or
        urlsplit(target).scheme!="https"):
        raise PermissionError("unsafe organizer redirect")
    if not _robots(client,final,robots_cache,target):
        raise PermissionError("robots disallow redirected organizer event")
    return client.get(target,headers=HEADERS,timeout=18,allow_redirects=False)

def enrich(conn,now,today,client=requests,max_pages=MAX_PAGES,sleep=time.sleep):
    conn.execute("""CREATE TABLE IF NOT EXISTS organizer_venue_checks(
        url TEXT PRIMARY KEY, checked_at TEXT NOT NULL,
        result TEXT NOT NULL, venue TEXT NOT NULL DEFAULT '')""")
    # Re-evaluate negative historical checks after any parser update,
    # while preserving the five-day cache for already checked URLs.
    columns={x[1] for x in conn.execute("PRAGMA table_info(organizer_venue_checks)")}
    if "parser_version" not in columns:
        conn.execute("ALTER TABLE organizer_venue_checks ADD COLUMN parser_version TEXT NOT NULL DEFAULT ''")
    # Select only genuinely missing venues in ongoing/upcoming events.
    all_rows=conn.execute("""SELECT id,title,municipality,venue,organizer_url,start,
                           COALESCE("end",start) AS finish
        FROM events WHERE status='approved'
        AND substr(COALESCE("end",start),1,10)>=?
        ORDER BY CASE WHEN substr(start,1,10)>=? THEN 0 ELSE 1 END,
                 ABS(julianday(substr(start,1,10))-julianday(?)),id
        LIMIT 2000""",(today.isoformat(),today.isoformat(),today.isoformat())).fetchall()
    rows=[row for row in all_rows if not venue_quality.named_venue(dict(row))]
    check_cache={}
    page_cache={}  # Only same-run official program pages; never browser storage.
    checked=updated=skipped_cache=eligible=0
    errors=[]
    for event in rows:
        url=valid_url(event["organizer_url"])
        if not url:continue
        eligible+=1
        old=conn.execute("SELECT checked_at,result,venue,parser_version FROM organizer_venue_checks WHERE url=?",(url,)).fetchone()
        if old:
            # Cached successes may enrich another event sharing the same URL
            # only when its title also matches; no blind cross-event assignment.
            try:age=(dt.datetime.fromisoformat(now)-dt.datetime.fromisoformat(old[0])).total_seconds()
            except (ValueError,TypeError):age=10**9
            if (urlsplit(url).hostname.removeprefix("www.") not in
                structured_organizer_venues.SUPPORTED_HOSTS and
                age<CACHE_DAYS*86400 and old[3]==PARSER_VERSION):
                skipped_cache+=1
                continue
        cached_page=url in page_cache
        if checked>=max_pages and not cached_page:break
        host=urlsplit(url).hostname.lower()
        try:
            if cached_page:
                soup=page_cache[url]
            else:
                # Check robots policy before requesting an organizer document.
                if not _robots(client,host,check_cache,url):raise PermissionError("robots disallow organizer event")
                r=client.get(url,headers=HEADERS,timeout=18,allow_redirects=False)
                r=_same_official_redirect(client,url,r,check_cache)
                if r.status_code!=200:raise RuntimeError("organizer HTTP "+str(r.status_code))
                if len(r.content)>1_200_000 or "html" not in r.headers.get("content-type","text/html"):
                    raise ValueError("unexpected organizer document")
                soup=BeautifulSoup(r.content,"html.parser")
                if structured_organizer_venues.host_of(url) in structured_organizer_venues.SUPPORTED_HOSTS:
                    page_cache[url]=soup
            if not title_matches(soup,event["title"]):
                candidate=""
            else:
                candidate=structured_organizer_venues.extract(
                    soup,url,event["municipality"],event["start"][:10],
                    event["start"][11:16] if len(event["start"])>=16 else ""
                ) or parse_official(soup,event["title"],event["municipality"])
            if re.search(r"\b\d{1,3}\.\d{5,}",candidate):
                candidate=""
            if candidate and not structured_organizer_venues.municipality_consistent(
                soup,url,event["municipality"],candidate
            ):
                candidate=""
            outcome="verified" if candidate else "no_unambiguous_venue"
            if candidate:
                conn.execute("""UPDATE events SET venue=?,updated_at=? WHERE id=?""",
                    (candidate,now,event["id"]))
                updated+=int(conn.execute("SELECT changes()").fetchone()[0]>0)
        except (requests.RequestException,PermissionError,RuntimeError,ValueError) as exc:
            outcome=type(exc).__name__
            candidate=""
            if len(errors)<6:errors.append(str(exc)[:90])
        conn.execute("""INSERT INTO organizer_venue_checks(url,checked_at,result,venue,parser_version)
              VALUES(?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET
              checked_at=excluded.checked_at,result=excluded.result,
              venue=excluded.venue,parser_version=excluded.parser_version""",
              (url,now,outcome,candidate,PARSER_VERSION))
        if not cached_page:
            checked+=1
            sleep(0.35)
    conn.commit()
    return {"source":NAME,"checked_at":now,"found":checked,
            "added":0,"changed":updated,"verified_venues":updated,
            "eligible_missing":eligible,"skipped_cached":skipped_cache,
            "max_pages":max_pages,"error":("; ".join(errors[:3]) if errors else "")}
