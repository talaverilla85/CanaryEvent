#!/usr/bin/env python3
"""CanaryEvent official-source synchronizer. No scraping of commercial aggregators.
GitHub Actions persists data/events.sqlite and publishes public/events.json.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "events.sqlite"
PUBLIC = ROOT / "public"
TZ = ZoneInfo("Atlantic/Canary")
TODAY = dt.datetime.now(TZ).date()
NOW = dt.datetime.now(TZ).isoformat(timespec="seconds")
USER_AGENT = "CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent; official event discovery)"
MONTHS = {"ene":1,"feb":2,"mar":3,"abr":4,"may":5,"jun":6,"jul":7,"ago":8,"sep":9,"set":9,"oct":10,"nov":11,"dic":12,
          "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
PLACES = {
"Agaete":(28.100,-15.700),"Agüimes":(27.906,-15.445),"Artenara":(28.019,-15.647),
"Arucas":(28.119,-15.523),"Firgas":(28.106,-15.563),"Gáldar":(28.145,-15.654),
"Ingenio":(27.918,-15.436),"La Aldea de San Nicolás":(27.983,-15.780),
"Las Palmas de Gran Canaria":(28.124,-15.436),"Mogán":(27.884,-15.723),
"Moya":(28.108,-15.582),"San Bartolomé de Tirajana":(27.923,-15.573),
"Santa Brígida":(28.035,-15.497),"Santa Lucía de Tirajana":(27.914,-15.542),
"Santa María de Guía":(28.139,-15.632),"Tejeda":(27.996,-15.615),
"Telde":(27.993,-15.416),"Teror":(28.060,-15.546),"Valleseco":(28.045,-15.579),
"Valsequillo":(27.985,-15.497),"Vega de San Mateo":(28.010,-15.532)}
SOURCES = [
 {"name":"Ayuntamiento de Ingenio","url":"https://ingenio.es/events/","parser":"ingenio"},
 {"name":"Ayuntamiento de Agüimes","url":"https://eventos.aguimes.es/","parser":"aguimes"},
 {"name":"Juventud Las Palmas de Gran Canaria","url":"https://actividadesjuventud.laspalmasgc.es/","parser":"juventud"},
 {"name":"Circuito de Artes Escénicas GC","url":"https://artesescenicasgrancanaria.com/agenda.html","parser":"artes"},
]
HEADERS={"User-Agent":USER_AGENT,"Accept":"text/html,application/xhtml+xml"}
DB.parent.mkdir(parents=True,exist_ok=True)
PUBLIC.mkdir(parents=True,exist_ok=True)

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").lower())
    return re.sub(r"[^a-z0-9]+","-", "".join(c for c in s if not unicodedata.combining(c))).strip("-")

def category(title):
    t=norm(title)
    for name,words in [
       ("musica",("musica","concierto","tributo","cantante","canto","acustico","festival-musical")),
       ("familia",("infantil","familiar","ninos","taller","caballo","juegos","terror")),
       ("deporte",("carrera","competicion","campeonato","torneo","subida","cross","deportiva","ferrata")),
       ("gastronomia",("feria","gastronomia","tapas","mercado","gastronomica")),
       ("naturaleza",("senderismo","visita","excursion","ruta","parque")),
       ("cultura",("teatro","espectaculo","arte","exposicion","danza","cine"))]:
        if any(w in t for w in words):return name
    return "ocio"

def iso_start(day,month,year,time_value):
    if not (1<=int(day)<=31 and 1<=int(month)<=12):raise ValueError("invalid date")
    if not re.fullmatch(r"\d{2}:\d{2}",str(time_value)):raise ValueError("missing verified time")
    date=dt.date(int(year),int(month),int(day))
    if date<TODAY or date>TODAY+dt.timedelta(days=180):return None
    return f"{date.isoformat()}T{time_value}:00"

def year_for(month,day):
    d=dt.date(TODAY.year,month,day)
    if d<TODAY-dt.timedelta(days=45):d=d.replace(year=d.year+1)
    return d.year

def allowed(url):
    p=urlparse(url); base=f"{p.scheme}://{p.netloc}"
    if p.scheme!="https":raise ValueError("https required")
    r=requests.get(base+"/robots.txt",headers=HEADERS,timeout=12)
    if r.status_code!=200:raise RuntimeError(f"robots.txt unavailable (HTTP {r.status_code})")
    rp=RobotFileParser();rp.parse(r.text.splitlines())
    if not rp.can_fetch(USER_AGENT,url):raise PermissionError("robots disallows this URL")

def get_html(url):
    allowed(url)
    r=requests.get(url,headers=HEADERS,timeout=23,allow_redirects=False)
    r.raise_for_status()
    if len(r.content)>2_500_000:raise ValueError("document too big")
    return BeautifulSoup(r.content,"html.parser")

def clean(text,maxchars=250):
    return " ".join(str(text or "").split())[:maxchars]

def cancelled_jsonld_urls(soup):
    urls=set()
    def visit(node):
        if isinstance(node,list):
            for item in node:visit(item)
        elif isinstance(node,dict):
            kinds=node.get("@type",[])
            if isinstance(kinds,str):kinds=[kinds]
            if "Event" in kinds and str(node.get("eventStatus","")).endswith("EventCancelled"):
                offers=node.get("offers",{})
                links=[node.get("url")]
                if isinstance(offers,dict):links.append(offers.get("url"))
                for link in links:
                    if isinstance(link,str) and link.startswith("https://"):
                        urls.add(link.strip("/").lower())
            for value in node.values():
                if isinstance(value,(dict,list)):visit(value)
    for tag in soup.select('script[type="application/ld+json"]'):
        try:visit(json.loads(tag.string or tag.get_text()))
        except (TypeError,ValueError):pass
    return urls

def extract_ingenio(soup):
    found=[]
    cancelled_urls=cancelled_jsonld_urls(soup)
    for art in soup.select("article.mec-event-article"):
        title_el=art.select_one("h3.mec-event-title a[href]")
        date_el=art.select_one(".mec-start-date-label")
        time_el=art.select_one(".mec-start-time")
        if not (title_el and date_el and time_el):continue
        title=clean(title_el.get_text(" ",strip=True),180)
        mt=re.search(r"(\d{1,2})\s+([a-záéíóú]+)",date_el.get_text(" ",strip=True).lower())
        if not mt:continue
        month=MONTHS.get(norm(mt.group(2))[:3])
        if not month:continue
        klass=" ".join(art.get("class",[]))
        ym=re.search(r"mec-toggle-(20\d{2})(\d{2})",klass)
        year=int(ym.group(1)) if ym else year_for(month,int(mt.group(1)))
        if ym and int(ym.group(2))!=month:year=year_for(month,int(mt.group(1)))
        start=iso_start(int(mt.group(1)),month,year,clean(time_el.get_text(),5))
        if not start:continue
        end_el=art.select_one(".mec-end-time")
        end=None
        if end_el:
            endtime=clean(end_el.get_text(),5)
            if re.fullmatch(r"\d{2}:\d{2}",endtime) and endtime>start[11:16]:
                end=start[:11]+endtime+":00"
        venue_el=art.select_one(".mec-venue-details > span")
        venue=clean(venue_el.get_text(" ",strip=True),150) if venue_el else ""
        address=art.select_one(".mec-event-address")
        if address and clean(address.get_text(" ",strip=True)):
            venue=clean(venue+" · "+address.get_text(" ",strip=True),180)
        desc=art.select_one(".mec-event-description")
        details=clean(desc.get_text(" ",strip=True),280) if desc else ""
        source_url=urljoin("https://ingenio.es/",title_el.get("href",""))
        if not source_url.startswith("https://"):continue
        if not title or len(title)<5 or not venue:continue
        found.append(dict(title=title,start=start,end=end,municipality="Ingenio",venue=venue,
             category=category(title),free=None,price="",details=details,
             source_name="Ayuntamiento de Ingenio",source_url=source_url,
             status="cancelled" if re.match(r"^(cancelad[oa]|suspendid[oa])\b",title,re.I) or source_url.strip("/").lower() in cancelled_urls else "approved"))
    return found

def extract_aguimes(soup):
    found=[]
    for node in soup.select("div.event"):
        title_el=node.select_one(".name a[href]")
        date_el=node.select_one(".date")
        venue_el=node.select_one(".place")
        if not (title_el and date_el and venue_el):continue
        title=clean(title_el.get_text(" ",strip=True),180)
        date_text=norm(date_el.get_text(" ",strip=True)).replace("-", " ")
        raw=clean(date_el.get_text(" ",strip=True).lower(),120)
        mt=re.search(r"(\d{1,2})\s*,?\s*([a-záéíóú]{3,})\.?\s*(?:a las|,)?\s*(\d{1,2}:\d{2})",raw)
        if not mt:continue
        month=MONTHS.get(norm(mt.group(2))[:3]);day=int(mt.group(1))
        if not month:continue
        start=iso_start(day,month,year_for(month,day),mt.group(3).zfill(5))
        if not start:continue
        venue=clean(venue_el.get_text(" ",strip=True),180)
        if not venue or len(title)<5:continue
        muni="Santa Lucía de Tirajana" if any(w in norm(venue) for w in ("vecindario","santa-lucia")) else "Agüimes"
        badge=node.select_one("span.bg-gray-200")
        badge_text=clean(badge.get_text(" ",strip=True),80).lower() if badge else ""
        is_free=1 if "gratuit" in badge_text else None
        extra=node.select_one("span.bg-blue-200")
        details=clean(extra.get_text(" ",strip=True),270) if extra else "Consulta disponibilidad y requisitos en la fuente oficial."
        url=urljoin("https://eventos.aguimes.es/",title_el.get("href",""))
        if not url.startswith("https://eventos.aguimes.es/"):continue
        found.append(dict(title=title,start=start,end=None,municipality=muni,venue=venue,category=category(title),
                          free=is_free,price="Gratis" if is_free else "",details=details,
                          source_name="Ayuntamiento de Agüimes",source_url=url,
                          status="cancelled" if re.match(r"^(cancelad[oa]|suspendid[oa])\b",title,re.I) else "approved"))
    return found


def extract_juventud(soup):
    found=[]
    for node in soup.select("div.event"):
        title_el=node.select_one(".name a[href]")
        date_el=node.select_one(".date")
        venue_el=node.select_one(".place")
        if not (title_el and date_el and venue_el):continue
        title=clean(title_el.get_text(" ",strip=True),180)
        raw=clean(date_el.get_text(" ",strip=True).lower(),120)
        if " - " in raw:continue  # Recurring sessions aren't dated individually
        mt=re.search(r"(\d{1,2})\s*,?\s*([a-záéíóú]{3,})\.?\s*(?:a las|,)?\s*(\d{1,2}:\d{2})",raw)
        if not mt:continue
        month=MONTHS.get(norm(mt.group(2))[:3]);day=int(mt.group(1))
        if not month:continue
        start=iso_start(day,month,year_for(month,day),mt.group(3).zfill(5))
        if not start:continue
        venue=clean(venue_el.get_text(" ",strip=True),180)
        url=urljoin("https://actividadesjuventud.laspalmasgc.es/",title_el.get("href",""))
        if not url.startswith("https://actividadesjuventud.laspalmasgc.es/events/") or not venue or len(title)<5:continue
        badge=node.select_one("span.bg-gray-200")
        badge_text=clean(badge.get_text(" ",strip=True)).lower() if badge else ""
        is_free=1 if "gratuit" in badge_text else None
        extra=node.select_one("span.bg-blue-200")
        details=clean(extra.get_text(" ",strip=True),270) if extra else "Consulta requisitos y disponibilidad con Juventud Las Palmas."
        found.append(dict(title=title,start=start,end=None,municipality="Las Palmas de Gran Canaria",
         venue=venue,category=category(title),free=is_free,price="Gratis" if is_free else "",details=details,
         source_name="Juventud Las Palmas de Gran Canaria",source_url=url,
         status="cancelled" if re.match(r"^(cancelad[oa]|suspendid[oa])\b",title,re.I) else "approved"))
    return found


def extract_artes(soup):
    found=[]
    for node in soup.select("div.agenda_evento"):
        title_el=node.select_one(".agenda_tituloevento")
        zone_el=node.select_one(".calendar_zonaevento")
        link_el=node.select_one('a[href^="evento-"]')
        if not (title_el and zone_el and link_el):continue
        title=clean(title_el.get_text(" ",strip=True),180)
        zone=clean(zone_el.get_text(" ",strip=True),180)
        if "," not in zone:continue
        city,venue=map(str.strip,zone.split(",",1))
        muni={
            "guia de gran canaria":"Santa María de Guía",
            "las palmas de gran canaria":"Las Palmas de Gran Canaria",
            "san bartolome de tirajana":"San Bartolomé de Tirajana",
            "santa lucia":"Santa Lucía de Tirajana",
        }.get(norm(city).replace("-"," "))
        if not muni:
            muni=next((m for m in PLACES if norm(m)==norm(city)),None)
        if not muni or not venue or len(title)<5:continue
        href=urljoin("https://artesescenicasgrancanaria.com/",link_el.get("href",""))
        if not href.startswith("https://artesescenicasgrancanaria.com/evento-"):continue
        syn=node.select_one(".agenda_synopsis")
        details=clean(syn.get_text(" ",strip=True),220) if syn else ""
        for row in node.select("table.mtable tr"):
            date=clean(row.get_text(" ",strip=True),230)
            mt=re.search(r"(\d{2})/(\d{2})/(20\d{2})",date)
            cells=row.select("td")
            if not (mt and len(cells)>=2):continue
            match_time=re.search(r"\b([0-2]\d:[0-5]\d)\b",cells[1].get_text(" ",strip=True))
            if not match_time:continue
            start=iso_start(int(mt.group(1)),int(mt.group(2)),int(mt.group(3)),match_time.group(1))
            if not start:continue
            found.append(dict(title=title,start=start,end=None,municipality=muni,venue=venue,
                category=category(title) if category(title)!="ocio" else "cultura",
                free=None,price="",details=details,source_name="Circuito de Artes Escénicas GC",
                source_url=href,status="cancelled" if re.match(r"^(cancelad[oa]|suspendid[oa])\b",title,re.I) else "approved"))
    return found

def init(conn):
    conn.executescript("""
       CREATE TABLE IF NOT EXISTS events(
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         dedup_key TEXT UNIQUE NOT NULL,
         title TEXT NOT NULL, start TEXT NOT NULL, "end" TEXT,
         municipality TEXT NOT NULL, venue TEXT NOT NULL,
         category TEXT NOT NULL, free INTEGER, price TEXT, details TEXT,
         lat REAL, lng REAL, accuracy TEXT DEFAULT 'municipality',
         source_name TEXT NOT NULL, source_url TEXT NOT NULL,
         status TEXT NOT NULL DEFAULT 'approved',
         created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_seen TEXT NOT NULL);
       CREATE INDEX IF NOT EXISTS idx_events_start ON events(start,status);
       CREATE TABLE IF NOT EXISTS source_log(
         source TEXT PRIMARY KEY, checked_at TEXT, found INTEGER DEFAULT 0,
         added INTEGER DEFAULT 0, changed INTEGER DEFAULT 0, error TEXT);
    """)
    # One-time migration: identity stays stable when the organizer changes the hour
    # on the same day. Do not lose old rows or erase legitimate duplicates.
    for old in conn.execute("SELECT id,dedup_key,title,start,municipality FROM events").fetchall():
        current=dedup_key(dict(old))
        if current!=old["dedup_key"]:
            try:
                conn.execute("UPDATE events SET dedup_key=? WHERE id=?",(current,old["id"]))
            except sqlite3.IntegrityError:
                pass

def dedup_key(e):
    title=str(e["title"]).strip()
    for prefix in ("cancelado","cancelada","suspendido","suspendida"):
        if norm(title).startswith(prefix+"-"):
            title=title[len(prefix):].lstrip(" :-")
            break
    return hashlib.sha256((norm(title)+"|"+e["start"][:10]+"|"+norm(e["municipality"])).encode()).hexdigest()[:32]

def upsert(conn,e):
    key=dedup_key(e)
    lat,lng=PLACES[e["municipality"]]
    # A record disappearing from a listing is NOT evidence of cancellation.
    existing=conn.execute("SELECT * FROM events WHERE dedup_key=?",(key,)).fetchone()
    cols=(e["title"],e["start"],e.get("end"),e["municipality"],e["venue"],e["category"],
        e["free"],e["price"],e["details"],lat,lng,e["source_name"],e["source_url"],e["status"])
    if existing:
        old=(existing["title"],existing["start"],existing["end"],existing["municipality"],existing["venue"],
             existing["category"],existing["free"],existing["price"],existing["details"],existing["lat"],
             existing["lng"],existing["source_name"],existing["source_url"],existing["status"])
        if cols==old:
            conn.execute("UPDATE events SET last_seen=? WHERE dedup_key=?",(NOW,key))
            return "unchanged"
        conn.execute("""UPDATE events SET title=?,start=?,"end"=?,municipality=?,venue=?,category=?,free=?,price=?,
          details=?,lat=?,lng=?,source_name=?,source_url=?,status=?,updated_at=?,last_seen=?
          WHERE dedup_key=?""",cols+(NOW,NOW,key))
        return "changed"
    conn.execute("""INSERT INTO events(dedup_key,title,start,"end",municipality,venue,category,free,price,details,
     lat,lng,source_name,source_url,status,created_at,updated_at,last_seen)
     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(key,)+cols+(NOW,NOW,NOW))
    return "added"

def write_json(path, obj):
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    temp.replace(path)

def run():
    results=[]
    with sqlite3.connect(DB) as conn:
        conn.row_factory=sqlite3.Row
        init(conn)
        for src in SOURCES:
            found=added=changed=0; error=""
            try:
                soup=get_html(src["url"])
                extractor={"ingenio":extract_ingenio,"aguimes":extract_aguimes,"juventud":extract_juventud,"artes":extract_artes}[src["parser"]]
                entries=extractor(soup)
                # A wholesale parser break must not erase the last good catalog.
                if len(entries)==0:raise RuntimeError("No verified entries; parser or page may have changed")
                for entry in entries:
                    if entry["municipality"] not in PLACES:continue
                    found+=1
                    what=upsert(conn,entry)
                    if what=="added":added+=1
                    if what=="changed":changed+=1
                conn.commit()
            except Exception as exc:
                error=str(exc)[:300]; print(f"WARN {src['name']}: {error}",file=sys.stderr)
            conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
             VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
             checked_at=excluded.checked_at,found=excluded.found,added=excluded.added,
             changed=excluded.changed,error=excluded.error""",(src["name"],NOW,found,added,changed,error))
            conn.commit()
            results.append({"source":src["name"],"checked_at":NOW,"found":found,"added":added,"changed":changed,"error":error})
            print(f"{src['name']}: candidates={found} added={added} changed={changed} error={error[:100]}")
            time.sleep(0.4)
        rows=conn.execute("""SELECT * FROM events WHERE status='approved' AND substr(COALESCE("end",start),1,10)>=?
             ORDER BY start ASC LIMIT 1200""",(TODAY.isoformat(),)).fetchall()
        events=[]
        for row in rows:
            e={k:row[k] for k in ("id","title","start","end","municipality","venue","category",
                                  "free","price","details","lat","lng","accuracy","source_name","source_url")}
            events.append(e)
        total=conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        statuses=dict(conn.execute("SELECT status,COUNT(*) FROM events GROUP BY status").fetchall())
    write_json(PUBLIC/"events.json",{"events":events,"generated_at":NOW,"timezone":"Atlantic/Canary",
                                    "verified_sources":len([r for r in results if not r["error"]])})
    write_json(PUBLIC/"meta.json",{"checked_at":NOW,"sources":results,
        "counts":{"approved":len(events),"pending":0,"needs_review":0,"archived_or_expired":max(0,total-len(events)),
                  "cancelled":statuses.get("cancelled",0)},
        "description":"Actualización programada de fuentes oficiales. Un cambio o cancelación solo se afirma cuando está explícitamente indicado."})
    print(f"Exported {len(events)} future verified events; database rows {total}")
    return 0 if any(r["found"] for r in results) else 2

if __name__=="__main__":
    sys.exit(run())
