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
import artes_details
import cabildo_public
import ulpgc_venue_facts
import verified_venue_coordinates
import cross_source_venue_facts
import ticket_reserva
import ticket_recent
import santalucia_festivals
import arucas_agenda
import galdar_agenda
import santabrigida_agenda
import teror_auditorio
import telde_fiestas
import artenara_ferias
import valsequillo_medianias
import tejeda_agenda
import telde_barrio_programs
import telde_pdf_verified
import telde_pdf_integrity
import telde_pdf_auto
import municipal_pdf_sources
import municipal_pdf_auto
import gc_documented_events
import municipal_listing_dedup
import cinema_policy
import event_occurrences
import program_quality
import venue_quality
import organizer_venues
import ingenio_juvenil_program
from event_images import listing_image,image_fields

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
    # Under RFC 9309, a 404/410 means that no robots policy exists;
    # explicit Disallow still takes priority, and 401/403/5xx fail closed.
    if r.status_code in (404,410):
        return
    if r.status_code!=200:
        raise RuntimeError(f"robots.txt unavailable (HTTP {r.status_code})")
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
        image=listing_image(art,"https://ingenio.es/",[".mec-event-image img"])
        found[-1].update(image_fields(image,title,"Ayuntamiento de Ingenio"))
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
        image=listing_image(node,"https://eventos.aguimes.es/",["img.image"])
        found[-1].update(image_fields(image,title,"Ayuntamiento de Agüimes"))
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
        venue=clean(venue_el.get_text(" ",strip=True),180)
        url=urljoin("https://actividadesjuventud.laspalmasgc.es/",title_el.get("href",""))
        if not url.startswith("https://actividadesjuventud.laspalmasgc.es/events/") or not venue or len(title)<5:continue

        # Recurring activities publish actual ISO datetimes in the official
        # booking selector. These are VERIFIED sessions, not days extrapolated
        # from a broad start/end range. Ignore "__more__" and other controls.
        sessions=[]
        for option in node.select('select[name="reserved_at"] option[value]'):
            value=str(option.get("value","")).strip()
            if not re.fullmatch(r"20\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",value):continue
            try:session=dt.datetime.strptime(value,"%Y-%m-%d %H:%M:%S")
            except ValueError:continue
            if TODAY<=session.date()<=TODAY+dt.timedelta(days=180):
                sessions.append(session.isoformat(timespec="seconds"))
        sessions=sorted(set(sessions))
        recurring=bool(sessions)
        if not sessions:
            # No dated options? A range alone is NOT permission to create
            # guessed weekly sessions. Keep the original single-day parser.
            if " - " in raw:continue
            mt=re.search(r"(\d{1,2})\s*,?\s*([a-záéíóú]{3,})\.?\s*(?:a las|,)?\s*(\d{1,2}:\d{2})",raw)
            if not mt:continue
            month=MONTHS.get(norm(mt.group(2))[:3]);day=int(mt.group(1))
            if not month:continue
            start=iso_start(day,month,year_for(month,day),mt.group(3).zfill(5))
            if not start:continue
            sessions=[start]

        badge=node.select_one("span.bg-gray-200")
        badge_text=clean(badge.get_text(" ",strip=True)).lower() if badge else ""
        is_free=1 if "gratuit" in badge_text else None
        extra=node.select_one("span.bg-blue-200")
        details=clean(extra.get_text(" ",strip=True),200) if extra else "Consulta requisitos y disponibilidad con Juventud Las Palmas."
        if recurring:
            details=clean(details+" Fecha y hora extraídas del selector oficial; consulta plazas e inscripción.",270)
        picture=image_fields(listing_image(node,"https://actividadesjuventud.laspalmasgc.es/",["img.image"]),title,"Juventud Las Palmas")
        for start in sessions:
            item=dict(title=title,start=start,end=None,municipality="Las Palmas de Gran Canaria",
                venue=venue,category=category(title),free=is_free,price="Gratis" if is_free else "",
                details=details,source_name="Juventud Las Palmas de Gran Canaria",source_url=url,
                status="cancelled" if re.match(r"^(cancelad[oa]|suspendid[oa])\b",title,re.I) else "approved")
            item.update(picture)
            found.append(item)
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
        details="Más información sobre el espectáculo en la ficha oficial."
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
            image=listing_image(node,"https://artesescenicasgrancanaria.com/geo",["img._imevent"])
            found[-1].update(image_fields(image,title,"Circuito de Artes Escénicas GC"))
    return found


def enrich_artes_entries(entries,conn):
    """Read the organizer's event detail page to complete ticket price,
    verified venue, duration and a short intelligible description.
    Persist a 48h cache so scheduled scans do not hammer the source.
    """
    conn.execute("""CREATE TABLE IF NOT EXISTS artes_detail_cache(
      url TEXT PRIMARY KEY, checked_at TEXT NOT NULL,
      venue TEXT NOT NULL DEFAULT '', price TEXT NOT NULL DEFAULT '',
      free INTEGER, details TEXT NOT NULL DEFAULT '', duration_min INTEGER)""")
    urls=list(dict.fromkeys(e["source_url"] for e in entries))
    detail_by_url={}
    requests_this_run=0
    for url in urls:
        old=conn.execute("SELECT * FROM artes_detail_cache WHERE url=?",(url,)).fetchone()
        use_cache=False
        if old:
            try:
                cache_age=(dt.datetime.fromisoformat(NOW)-dt.datetime.fromisoformat(old["checked_at"])).total_seconds()
                use_cache=cache_age<48*3600
            except (ValueError,TypeError):pass
        if use_cache:
            detail_by_url[url]={k:old[k] for k in ("venue","price","free","details","duration_min")}
            continue
        if requests_this_run>=12:
            if old:detail_by_url[url]={k:old[k] for k in ("venue","price","free","details","duration_min")}
            continue
        try:
            # get_html checks robots.txt and caps responses before parsing.
            page=get_html(url)
            detail=artes_details.parse_detail(page)
            detail_by_url[url]=detail
            conn.execute("""INSERT INTO artes_detail_cache
              (url,checked_at,venue,price,free,details,duration_min)
              VALUES(?,?,?,?,?,?,?)
              ON CONFLICT(url) DO UPDATE SET checked_at=excluded.checked_at,
                venue=excluded.venue,price=excluded.price,free=excluded.free,
                details=excluded.details,duration_min=excluded.duration_min""",
              (url,NOW,detail["venue"],detail["price"],detail["free"],detail["details"],detail["duration_min"]))
            requests_this_run+=1
            time.sleep(0.5)
        except (requests.RequestException,PermissionError,ValueError,RuntimeError) as exc:
            print(f"WARN Artes event detail {url}: {type(exc).__name__}",file=sys.stderr)
            if old:detail_by_url[url]={k:old[k] for k in ("venue","price","free","details","duration_min")}
    for e in entries:
        if e["source_url"] in detail_by_url:
            artes_details.apply_detail(e,detail_by_url[e["source_url"]])
    conn.commit()
    return entries

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
    # Safe migration of the existing SQLite database without deleting historical events.
    columns={row[1] for row in conn.execute("PRAGMA table_info(events)")}
    for field in ("image_url","image_alt","image_origin","image_status","organizer_url"):
        if field not in columns:
            conn.execute(f"ALTER TABLE events ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
    # One-time migration: identity stays stable when the organizer changes the hour
    # on the same day. Do not lose old rows or erase legitimate duplicates.
    for old in conn.execute("SELECT id,dedup_key,title,start,municipality,source_url FROM events").fetchall():
        current=dedup_key(dict(old))
        if current!=old["dedup_key"]:
            try:
                conn.execute("UPDATE events SET dedup_key=? WHERE id=?",(current,old["id"]))
            except sqlite3.IntegrityError:
                pass

def dedup_key(e):
    # A child activity can share its original Cabildo poster URL with
    # the umbrella programme. Give the individual activity a unique
    # stable key BEFORE the special Cabildo URL-ID branch below.
    if e.get("source_name")==ingenio_juvenil_program.NAME:
        child="juventud-ingenio:individual:"+norm(e["title"])+"|"+e["start"][:10]+"|"+norm(e["municipality"])
        return hashlib.sha256(child.encode()).hexdigest()[:32]
    url=str(e.get("source_url") or "")
    # One official event ID can distinguish separate screenings/sessions even
    # when titles and day match. Stable under time or venue corrections.
    if url.startswith("https://www.eventosgrancanaria.com/event/"):
        m=re.search(r"/event/(E-20\d{6}-\d{4})/",url)
        if m:
            return hashlib.sha256(("cabildo:"+m.group(1)).encode()).hexdigest()[:32]
    title=str(e["title"]).strip()
    for prefix in ("cancelado","cancelada","suspendido","suspendida"):
        if norm(title).startswith(prefix+"-"):
            title=title[len(prefix):].lstrip(" :-")
            break
    return hashlib.sha256((norm(title)+"|"+e["start"][:10]+"|"+norm(e["municipality"])).encode()).hexdigest()[:32]

def upsert(conn,e):
    key=dedup_key(e)
    lat,lng=PLACES[e["municipality"]]
    existing=conn.execute("SELECT * FROM events WHERE dedup_key=?",(key,)).fetchone()
    event_columns=("title","start","end","municipality","venue","category","free","price","details",
                   "lat","lng","accuracy","source_name","source_url","status",
                   "image_url","image_alt","image_origin","image_status","organizer_url")
    fields=dict(e)
    if existing and existing["status"]=="duplicate" and fields.get("status")=="approved":
        fields["status"]="duplicate"
    if existing and str(e.get("source_name","")).startswith("TuReservaOnline") and not existing["source_name"].startswith("TuReservaOnline"):
        fields["source_name"]=existing["source_name"]
        fields["source_url"]=existing["source_url"]
        if not existing["organizer_url"]:
            fields["organizer_url"]=e["source_url"]
        if existing["details"]:
            fields["details"]=existing["details"]
    # A verified organizer venue is more informative than a later generic
    # municipal placeholder: never erase it during a periodic source refresh.
    if existing and venue_quality.named_venue(dict(existing)) and not venue_quality.named_venue(fields):
        fields["venue"]=existing["venue"]
    lat,lng,accuracy=verified_venue_coordinates.resolve(fields["municipality"],fields.get("venue",""),PLACES)
    fields.update(lat=lat,lng=lng,accuracy=accuracy)
    for k in ("image_url","image_alt","image_origin","image_status","organizer_url"):
        fields.setdefault(k,"")
    values=tuple(fields.get(key) for key in event_columns)
    if existing:
        current=tuple(existing[key] for key in event_columns)
        if values==current:
            conn.execute("UPDATE events SET last_seen=? WHERE dedup_key=?",(NOW,key))
            return "unchanged"
        setters=",".join(('"' + key + '"=?') for key in event_columns)
        conn.execute("UPDATE events SET "+setters+",updated_at=?,last_seen=? WHERE dedup_key=?",
                     values+(NOW,NOW,key))
        return "changed"
    keys=("dedup_key",)+event_columns+("created_at","updated_at","last_seen")
    conn.execute("INSERT INTO events ("+",".join('"'+k+'"' for k in keys)+") VALUES("+
        ",".join("?" for _ in keys)+")",(key,)+values+(NOW,NOW,NOW))
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
                if src["parser"]=="artes":
                    entries=enrich_artes_entries(entries,conn)
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
        # Local patron-saint festivities not necessarily indexed by Cabildo.
        # Publication requires two official municipal pages to verify dates and
        # explicitly free entry; a parser failure must keep the last good data.
        town=santalucia_festivals
        local_found=local_added=local_changed=0
        local_error=""
        try:
            a=get_html(town.ANNOUNCEMENT)
            b=get_html(town.BRAULIO)
            items=town.extract(str(a),str(b),TODAY,norm,category,PLACES)
            for item in items:
                local_found+=1
                change=upsert(conn,item)
                local_added+=int(change=="added")
                local_changed+=int(change=="changed")
            conn.commit()
        except Exception as exc:
            local_error=str(exc)[:250]
            print(f"WARN Santa Lucia festivities: {local_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
           VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
           checked_at=excluded.checked_at,found=excluded.found,
           added=excluded.added,changed=excluded.changed,error=excluded.error""",
           (town.NAME,NOW,local_found,local_added,local_changed,local_error))
        conn.commit()
        results.append(dict(source=town.NAME,checked_at=NOW,found=local_found,
                    added=local_added,changed=local_changed,error=local_error))
        print(f"Santa Lucia festivities: found={local_found} new={local_added} error={local_error[:90]}")
        # Direct municipal listings capture town activities missing from Cabildo.
        # No inferred times, entry prices, or specific venues.
        arucas_found=arucas_added=arucas_changed=0
        arucas_error=""
        try:
            listing=arucas_agenda.fetch_listing()
            entries=arucas_agenda.extract(listing,TODAY,PLACES,norm,category)
            entries=arucas_agenda.enrich_venues(entries)
            for entry in entries:
                arucas_found+=1
                change=upsert(conn,entry)
                arucas_added+=int(change=="added")
                arucas_changed+=int(change=="changed")
            conn.commit()
        except Exception as exc:
            arucas_error=str(exc)[:250]
            print(f"WARN Arucas municipal agenda: {arucas_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
          VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
          checked_at=excluded.checked_at,found=excluded.found,
          added=excluded.added,changed=excluded.changed,error=excluded.error""",
          (arucas_agenda.NAME,NOW,arucas_found,arucas_added,arucas_changed,arucas_error))
        conn.commit()
        results.append({"source":arucas_agenda.NAME,"checked_at":NOW,"found":arucas_found,
                        "added":arucas_added,"changed":arucas_changed,"error":arucas_error})
        print(f"Arucas municipal agenda: found={arucas_found}, added={arucas_added}, changed={arucas_changed}, error={arucas_error[:100]}")
        # The Gáldar Culture EventON listing exposes verified schema.org
        # start/end times, venue and original event URLs.
        galdar_found=galdar_added=galdar_changed=0
        galdar_error=""
        try:
            listing=galdar_agenda.fetch_listing()
            entries=galdar_agenda.extract(listing,TODAY,PLACES,norm,category)
            for entry in entries:
                galdar_found+=1
                change=upsert(conn,entry)
                galdar_added+=int(change=="added")
                galdar_changed+=int(change=="changed")
            conn.commit()
        except Exception as exc:
            galdar_error=str(exc)[:250]
            print(f"WARN Galdar Culture agenda: {galdar_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
            VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
            checked_at=excluded.checked_at,found=excluded.found,
            added=excluded.added,changed=excluded.changed,error=excluded.error""",
            (galdar_agenda.NAME,NOW,galdar_found,galdar_added,galdar_changed,galdar_error))
        conn.commit()
        results.append({"source":galdar_agenda.NAME,"checked_at":NOW,"found":galdar_found,
                        "added":galdar_added,"changed":galdar_changed,"error":galdar_error})
        print(f"Galdar Culture agenda: found={galdar_found}, added={galdar_added}, changed={galdar_changed}, error={galdar_error[:100]}")
        # Official calendars and independently verified municipal notices.
        # They supplement rather than replace already-known Cabildo and ticket
        # events. Any source failure is isolated and recorded for transparency.
        new_municipal_sources=(
            # Tejeda: automatically inspect new official agenda articles.
            # Publication date must support each explicit future event date.
            (tejeda_agenda.NAME,
             lambda: tejeda_agenda.fetch_and_extract(TODAY,PLACES,category)),
            # Official 2026 intermunicipal source; preserve Valsequillo TLS safety.
            (valsequillo_medianias.NAME,
             lambda: valsequillo_medianias.extract(
                 valsequillo_medianias.fetch(),TODAY,PLACES,category)
             if TODAY<=dt.date(2026,11,1) else []),
            (artenara_ferias.NAME,
             lambda: artenara_ferias.extract(artenara_ferias.fetch(),TODAY,PLACES,category)
             if TODAY<=dt.date(2026,11,1) else []),
            (santabrigida_agenda.NAME,
             lambda: santabrigida_agenda.fetch_and_extract(TODAY,PLACES,category)),
            (teror_auditorio.NAME,
             lambda: teror_auditorio.extract(teror_auditorio.get_html(),TODAY,PLACES,category)
             if TODAY<=dt.date(2027,1,31) else []),
            (telde_fiestas.NAME,
             lambda: telde_fiestas.extract(telde_fiestas.read_official(),TODAY,PLACES,category)
             if TODAY<=dt.date(2026,11,17) else []),
        )
        for source_name,loader in new_municipal_sources:
            found=added=changed=0
            err=""
            try:
                entries=loader()
                for entry in entries:
                    if entry["municipality"] not in PLACES:continue
                    found+=1
                    result=upsert(conn,entry)
                    added+=int(result=="added")
                    changed+=int(result=="changed")
                conn.commit()
            except Exception as exc:
                err=str(exc)[:250]
                print(f"WARN {source_name}: {err}",file=sys.stderr)
            conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
                VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
                checked_at=excluded.checked_at,found=excluded.found,
                added=excluded.added,changed=excluded.changed,error=excluded.error""",
                (source_name,NOW,found,added,changed,err))
            conn.commit()
            results.append({"source":source_name,"checked_at":NOW,"found":found,
                            "added":added,"changed":changed,"error":err})
            print(f"{source_name}: verified={found} new={added} updated={changed} error={err[:100]}")
        # Monitor Telde neighbourhood PDF programs without inventing events.
        programs_path=PUBLIC/"municipal_programs.json"
        programs_error=""
        programs_found=0
        try:
            year=TODAY.year
            soup=telde_barrio_programs.fetch_year(year)
            found_pdf=telde_barrio_programs.extract(soup,year)
            old_pdf=[]
            if programs_path.exists():
                try:
                    old_obj=json.loads(programs_path.read_text(encoding="utf8"))
                    old_pdf=old_obj.get("programs",[])
                except (json.JSONDecodeError,OSError,AttributeError):
                    pass
            merged=telde_barrio_programs.merge_seen(found_pdf,old_pdf,NOW)
            programs_found=len(merged)
            write_json(programs_path,{"checked_at":NOW,"source_name":telde_barrio_programs.NAME,
                       "source_url":telde_barrio_programs.index_url(year),
                       "program_count":programs_found,"events_imported":0,
                       "note":"PDFs descubiertos, no eventos. Cada actividad requiere comprobación independiente.",
                       "programs":merged})
        except Exception as exc:
            programs_error=str(exc)[:250]
            print(f"WARN Telde PDF index: {programs_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
          VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
          checked_at=excluded.checked_at,found=excluded.found,added=0,
          changed=0,error=excluded.error""",
          (telde_barrio_programs.NAME,NOW,0,0,0,programs_error))
        conn.commit()
        results.append({"source":telde_barrio_programs.NAME,"checked_at":NOW,
                        "found":0,"added":0,"changed":0,"error":programs_error})
        print(f"Telde neighbourhood PDF programs: discovered={programs_found}, events imported=0, error={programs_error[:100]}")
        # Import only individual PDF acts that passed two independent visual
        # readings of the same official municipal PDF page. Uncertain AI output
        # stays in the private review queue and is never passed to upsert().
        pdf_verified_found=pdf_verified_added=pdf_verified_changed=0
        pdf_verified_error=""
        try:
            approved_path=ROOT/"data"/"telde_pdf_pilot"/"verified_events.json"
            if approved_path.exists():
                approved=json.loads(approved_path.read_text(encoding="utf8"))
                if not isinstance(approved,list):raise ValueError("Verified PDF registry must be a list")
                official_pdfs=set()
                if programs_path.exists():
                    programs_data=json.loads(programs_path.read_text(encoding="utf8"))
                    official_pdfs={x["pdf_url"] for x in programs_data.get("programs",[]) if x.get("year")==TODAY.year}
                scan_state=json.loads((ROOT/"data/telde_pdf_pilot/scan_state.json").read_text(encoding="utf8"))
                image_cache=json.loads((ROOT/"data/telde_pdf_pilot/vision_cache.json").read_text(encoding="utf8"))
                seen=set()
                trusted_events=[]
                for item in approved:
                    if not telde_pdf_integrity.trusted(
                            item,official_pdfs,scan_state,image_cache,TODAY,
                            telde_pdf_auto.tv.MODEL,telde_pdf_auto.VERSION):continue
                    entry=telde_pdf_verified.approved_to_event(item)
                    key=(norm(entry["title"]),entry["start"],norm(entry["venue"]))
                    if key in seen:continue
                    seen.add(key)
                    trusted_events.append(entry)
                    pdf_verified_found+=1
                    change=upsert(conn,entry)
                    pdf_verified_added+=int(change=="added")
                    pdf_verified_changed+=int(change=="changed")
                # Garbage-collect discredited test/old PDF rows, never other sources.
                removed=telde_pdf_integrity.cleanup_stale(conn,trusted_events)
                if removed:
                    print(f"WARN Removed {removed} PDF-only listings without actual source proof")
                conn.commit()
                if programs_path.exists() and pdf_verified_found:
                    programs_data["events_imported"]=pdf_verified_found
                    programs_data["note"]="PDFs oficiales descubiertos; solo se importan actividades validadas por dos lecturas visuales independientes."
                    write_json(programs_path,programs_data)
        except Exception as exc:
            pdf_verified_error=str(exc)[:250]
            print(f"WARN PDF double-verified events: {pdf_verified_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
         VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
         checked_at=excluded.checked_at,found=excluded.found,
         added=excluded.added,changed=excluded.changed,error=excluded.error""",
         (telde_pdf_verified.SOURCE,NOW,pdf_verified_found,pdf_verified_added,
          pdf_verified_changed,pdf_verified_error))
        conn.commit()
        results.append({"source":telde_pdf_verified.SOURCE,"checked_at":NOW,
                        "found":pdf_verified_found,"added":pdf_verified_added,
                        "changed":pdf_verified_changed,"error":pdf_verified_error})
        print(f"Telde PDF independently verified: found={pdf_verified_found} new={pdf_verified_added} error={pdf_verified_error[:80]}")
        # Other official municipal PDF programmes use the same two-pass
        # evidence gate as Telde. They must never replace a stronger,
        # independently listed record with the same normalized title and date.
        multi_found=multi_added=multi_changed=multi_duplicates=0
        multi_error=""
        try:
            multi_dir=ROOT/"data"/"municipal_pdf_pilot"
            multi_index=PUBLIC/"municipal_pdf_programs.json"
            if multi_index.exists():
                indexed=json.loads(multi_index.read_text(encoding="utf8"))
                programs={(d["pdf_url"],d["municipality"]):d
                          for d in indexed.get("programs",[])
                          if d.get("municipality") in municipal_pdf_sources.SOURCES
                          and d.get("year")==TODAY.year
                          and municipal_pdf_sources.verified_pdf(
                              d.get("pdf_url",""),d["municipality"],TODAY.year)}
                approved_path=multi_dir/"verified_events.json"
                verified_rows=json.loads(approved_path.read_text(encoding="utf8")) if approved_path.exists() else []
                if not isinstance(verified_rows,list):
                    raise ValueError("Municipal PDF verified events must be a list")
                state_path=multi_dir/"scan_state.json"
                cache_path=multi_dir/"vision_cache.json"
                scan_state=json.loads(state_path.read_text(encoding="utf8")) if state_path.exists() else {}
                cache=json.loads(cache_path.read_text(encoding="utf8")) if cache_path.exists() else {}
                verified_keys=set()
                seen=set()
                for item in verified_rows:
                    municipality=item.get("municipality")
                    url=item.get("pdf_url")
                    if (url,municipality) not in programs or municipality not in PLACES:
                        continue
                    if not telde_pdf_integrity.trusted(
                            item,{url},scan_state,cache,TODAY,
                            municipal_pdf_auto.vision.MODEL,municipal_pdf_auto.VERSION):
                        continue
                    entry=telde_pdf_verified.approved_to_event(item)
                    dedup=dedup_key(entry)
                    if dedup in seen:
                        continue
                    seen.add(dedup)
                    existing=conn.execute("SELECT source_name FROM events WHERE dedup_key=?",
                                          (dedup,)).fetchone()
                    if existing and existing["source_name"]!=entry["source_name"]:
                        multi_duplicates+=1
                        continue
                    verified_keys.add((entry["title"],entry["start"],entry["source_url"]))
                    multi_found+=1
                    action=upsert(conn,entry)
                    multi_added+=int(action=="added")
                    multi_changed+=int(action=="changed")
                for municipality in municipal_pdf_sources.SOURCES:
                    src="Ayuntamiento de "+municipality+" · programas PDF verificados (doble lectura IA)"
                    rows=conn.execute("SELECT id,title,start,source_url FROM events WHERE source_name=?",
                                      (src,)).fetchall()
                    stale=[(r["id"],) for r in rows
                           if (r["title"],r["start"],r["source_url"]) not in verified_keys]
                    if stale:
                        conn.executemany("DELETE FROM events WHERE id=?",stale)
                conn.commit()
        except Exception as exc:
            multi_error=type(exc).__name__+": "+str(exc)[:200]
            print(f"WARN municipal PDF verified feed: {multi_error}",file=sys.stderr)
        multi_source="Ayuntamientos · programas PDF verificados"
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
                       VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
                       checked_at=excluded.checked_at,found=excluded.found,
                       added=excluded.added,changed=excluded.changed,error=excluded.error""",
                     (multi_source,NOW,multi_found,multi_added,multi_changed,multi_error))
        conn.commit()
        results.append({"source":multi_source,"checked_at":NOW,
                        "found":multi_found,"added":multi_added,
                        "changed":multi_changed,"duplicates":multi_duplicates,
                        "error":multi_error})
        print(f"Other municipal PDF verified: {multi_found} acts, "
              f"{multi_duplicates} skipped duplicates; error={multi_error[:80]}")
        # Municipal notices independently reviewed for an unambiguous
        # future day, time and named venue. Do not overwrite stronger listings.
        documented_rows,documented_audit=gc_documented_events.extract(
            get_html,TODAY,PLACES)
        dc_found=dc_added=dc_changed=dc_collisions=0
        for entry in documented_rows:
            key=dedup_key(entry)
            old=conn.execute("SELECT source_name FROM events WHERE dedup_key=?",
                             (key,)).fetchone()
            if old and old["source_name"]!=entry["source_name"]:
                dc_collisions+=1
                continue
            dc_found+=1
            change=upsert(conn,entry)
            dc_added+=int(change=="added")
            dc_changed+=int(change=="changed")
        conn.commit()
        dc_error="; ".join(
            a["municipality"]+": "+a.get("error_type","source mismatch")
            for a in documented_audit
            if a["status"] in ("source_error","unverified_text"))[:250]
        documented_source="Ayuntamientos · actos individualmente contrastados"
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
                 VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
                 checked_at=excluded.checked_at,found=excluded.found,
                 added=excluded.added,changed=excluded.changed,error=excluded.error""",
            (documented_source,NOW,dc_found,dc_added,dc_changed,dc_error))
        conn.commit()
        results.append({"source":documented_source,"checked_at":NOW,
                        "found":dc_found,"added":dc_added,"changed":dc_changed,
                        "duplicates_skipped":dc_collisions,
                        "municipal_sources_checked":documented_audit,
                        "error":dc_error})
        print(f"Documented municipal notices: {dc_found} verified, "
              f"{dc_collisions} existing listings preserved, error={dc_error[:80]}")
        # Official campaign posters are sources, not individual plans.
        youth=ingenio_juvenil_program
        youth_found=youth_added=youth_changed=0
        youth_error=""
        try:
            if TODAY<=youth.PUBLISH_THROUGH:
                official=get_html(youth.PROGRAM_URL)
                youth_entries=youth.extract(str(official),TODAY,PLACES)
                for entry in youth_entries:
                    youth_found+=1
                    change=upsert(conn,entry)
                    youth_added+=int(change=="added")
                    youth_changed+=int(change=="changed")
                conn.commit()
        except Exception as exc:
            youth_error=str(exc)[:250]
            print(f"WARN youth poster breakdown: {youth_error}",file=sys.stderr)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
          VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
          checked_at=excluded.checked_at,found=excluded.found,
          added=excluded.added,changed=excluded.changed,error=excluded.error""",
          (youth.NAME,NOW,youth_found,youth_added,youth_changed,youth_error))
        conn.commit()
        results.append({"source":youth.NAME,"checked_at":NOW,"found":youth_found,
                        "added":youth_added,"changed":youth_changed,"error":youth_error})
        print(f"Juventud Ingenio individual events: found={youth_found} added={youth_added} error={youth_error[:100]}")
        # Public official event metadata: incremental polite scan, no photos or source descriptions.
        try:
            cabildo=cabildo_public.synchronize(conn,NOW,TODAY,PLACES,norm,category,upsert)
        except Exception as exc:
            cabildo={"source":cabildo_public.SOURCE_NAME,"checked_at":NOW,"found":0,
                "added":0,"changed":0,"scanned":0,"error":str(exc)[:300]}
        results.append(cabildo)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
         VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
         checked_at=excluded.checked_at,found=excluded.found,added=excluded.added,
         changed=excluded.changed,error=excluded.error""",
         (cabildo["source"],NOW,cabildo["found"],cabildo["added"],cabildo["changed"],cabildo.get("error","")))
        conn.commit()
        print(f"Cabildo: scanned={cabildo.get('scanned')} found={cabildo['found']} added={cabildo['added']} error={cabildo.get('error','')[:100]}")
        # Read only active, public ticket-listing facts from TuReservaOnline.
        # This is a separate data source, filtered strictly to Gran Canaria.
        # Run AFTER municipal sources so those remain the authoritative URL.
        try:
            tickets=ticket_reserva.synchronize(conn,NOW,TODAY,PLACES,norm,category,upsert)
        except Exception as exc:
            tickets={"source":ticket_reserva.NAME,"checked_at":NOW,
                 "found":0,"added":0,"changed":0,"error":str(exc)[:250]}
            print(f"WARN ticket source: {tickets['error']}",file=sys.stderr)
        if not tickets["error"]:
            try:
                recent=ticket_recent.reconcile_recent(conn,NOW,TODAY,PLACES,norm)
                tickets["recent_pages_checked"]=recent["examined"]
                tickets["changed"]+=recent["enriched"]
                print(f"TuReservaOnline individual details checked={recent['examined']} enriched={recent['enriched']}")
            except Exception as exc:
                print(f"WARN ticket detail matching: {type(exc).__name__}: {str(exc)[:100]}",file=sys.stderr)
        results.append(tickets)
        conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
          VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
          checked_at=excluded.checked_at,found=excluded.found,
          added=excluded.added,changed=excluded.changed,error=excluded.error""",
          (tickets["source"],NOW,tickets["found"],tickets["added"],tickets["changed"],tickets["error"]))
        conn.commit()
        print(f"TuReservaOnline: {tickets['found']} GC activities, +{tickets['added']} new, {tickets['changed']} matched/updated")
        # Secondary venue evidence: event-specific pages of approved official
        # organizers only; errors do not stop the daily catalogue update.
        try:
            venue_result=organizer_venues.enrich(conn,NOW,TODAY)
        except Exception as exc:
            venue_result={"source":organizer_venues.NAME,"checked_at":NOW,
                          "found":0,"added":0,"changed":0,"error":str(exc)[:250]}
        results.append(venue_result)
        print(f"Organizer venue checks: {venue_result.get('found',0)} updated={venue_result.get('changed',0)} error={venue_result.get('error','')[:100]}")
        # Secondary source confirmation salvages event locations when the
        # aggregator lacks a venue but a municipality has independently
        # published the exact same event on the same date.
        confirmed_cross_venues=cross_source_venue_facts.enrich(conn,NOW,TODAY)
        if confirmed_cross_venues["verified"]:
            print(f"Cross-source event places confirmed: {confirmed_cross_venues}")
        location_changes=verified_venue_coordinates.backfill(conn,PLACES)
        conn.commit()
        print(f"Verified venue coordinates refreshed for {location_changes} events")
        rows=conn.execute("""SELECT * FROM events WHERE status='approved' AND substr(COALESCE("end",start),1,10)>=?
             ORDER BY start ASC LIMIT 3500""",(TODAY.isoformat(),)).fetchall()
        events=[]
        for row in rows:
            e={k:row[k] for k in ("id","title","start","end","municipality","venue","category",
                                  "free","price","details","lat","lng","accuracy","source_name","source_url",
                                  "image_url","image_alt","image_origin","image_status","organizer_url")}
            events.append(ulpgc_venue_facts.enhance(e))
        # Apply the policy to old SQLite records, not only future imports.
        events,cinema_excluded=cinema_policy.remove_commercial_screenings(events)
        print(f"Routine commercial cinema excluded from public agenda: {len(cinema_excluded)}")
        # Quality-filter source records before projecting verified calendar
        # days: one brochure or theatre programme is not 30 sessions.
        events,programs_pending=program_quality.filter_public_plans(events)
        valid_candidates=len(events)
        events,venue_pending=venue_quality.split_verified(events)
        source_events=len(events)
        # A genuine two-day activity is two dated cards; a month-long
        # course remains one active range until individual sessions verified.
        daily_events=event_occurrences.expand(events,TODAY)
        occurrence_stats=event_occurrences.metrics(events,daily_events)
        # Deduplicate across sources AFTER day-by-day projection; never
        # erase the 29th just because the same source listed the 28th.
        events=municipal_listing_dedup.reconcile(daily_events,norm)
        occurrence_stats["post_dedup_cards"]=len(events)
        queue={"updated_at":NOW,
               "note":"Fichas pendientes de desglose o sin un evento identificable; no publicarlas como planes.",
               "pending_programs":programs_pending,
               "unverified_locations":[{**item,"source_url":ingenio_juvenil_program.PROGRAM_URL}
                                       for item in ingenio_juvenil_program.UNRESOLVED]}
        total=conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        statuses=dict(conn.execute("SELECT status,COUNT(*) FROM events GROUP BY status").fetchall())
    write_json(ROOT/"data"/"program_review_gc.json",queue)
    write_json(ROOT/"data"/"venue_review_gc.json",{
        "updated_at":NOW,"not_published":len(venue_pending),
        "note":"Actividades sin recinto verificado: guardadas en SQLite para revisar el organizador; no se publican como planes completos.",
        "events":venue_pending})
    write_json(PUBLIC/"events.json",{"events":events,"generated_at":NOW,"timezone":"Atlantic/Canary",
                                    "verified_sources":len([r for r in results if not r["error"]])})
    write_json(PUBLIC/"meta.json",{"checked_at":NOW,"sources":results,
        "occurrences":occurrence_stats,
        "counts":{"approved":len(events),"candidate_events":valid_candidates,
                  "verified_source_events_before_daily_projection":source_events,
                  "excluded_missing_venue":len(venue_pending),
                  "excluded_commercial_cinema":len(cinema_excluded),
                  "pending":0,"needs_review":len(programs_pending)+len(ingenio_juvenil_program.UNRESOLVED),
                  "archived_or_expired":max(0,total-valid_candidates),
                  "cancelled":statuses.get("cancelled",0),
                  "pdf_events_double_verified":pdf_verified_found,
                  "prices_confirmed":sum(bool(e["price"]) or e["free"]==1 for e in events),
                  "prices_to_verify":sum(not e["price"] and e["free"]!=1 for e in events),
                  "venues_to_verify":len(venue_pending),
                  "venues_verified":len(events)},
        "description":"Actualización programada de fuentes oficiales. Un cambio o cancelación solo se afirma cuando está explícitamente indicado."})
    print(f"Exported {len(events)} verified-venue plans; {len(venue_pending)} withheld for location verification; database rows {total}")
    return 0 if any(r["found"] for r in results) else 2

if __name__=="__main__":
    sys.exit(run())
