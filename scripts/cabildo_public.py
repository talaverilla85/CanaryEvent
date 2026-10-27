"""Conector incremental de metadatos públicos del portal oficial de eventos de Gran Canaria.
Lee SOLO datos fácticos (título, fecha, lugar, enlace), no fotografías, descripciones
ni credenciales publicadas en recursos web. No solicita páginas no indexadas.
Preserva una cola de URLs para evitar consultas masivas y controlar tráfico.
"""
import datetime as dt
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from event_images import official_page_image,image_fields
import source_facts

BASE="https://www.eventosgrancanaria.com"
SOURCE_NAME="Portal oficial de Eventos Gran Canaria (Cabildo)"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
MAX_PAGES_PER_RUN=75
MAX_LOOKAHEAD_DAYS=120
HEADERS={"User-Agent":AGENT,"Accept":"text/html"}
SESSION=requests.Session()
SESSION.headers.update(HEADERS)

def scan_allowed():
    from urllib.robotparser import RobotFileParser
    r=SESSION.get(BASE+"/robots.txt",timeout=15)
    r.raise_for_status()
    if "text/plain" not in r.headers.get("content-type",""):
        raise RuntimeError("Robots.txt not served as a text file")
    rp=RobotFileParser()
    rp.parse(r.text.splitlines())
    for path in ("/sitemap.xml","/event/E-20261024-0000/test"):
        if not rp.can_fetch(AGENT,BASE+path):
            raise PermissionError("Robots disallows public event scan")

def list_public_events():
    r=SESSION.get(BASE+"/sitemap.xml",timeout=20)
    r.raise_for_status()
    if len(r.content)>2_000_000:raise ValueError("Sitemap too large")
    root=ET.fromstring(r.content)
    urls=[]
    for el in root.findall(".//{*}loc"):
        if not el.text:continue
        u=el.text.strip()
        path=urlparse(u)
        if path.scheme!="https" or path.netloc!="www.eventosgrancanaria.com" or not re.fullmatch(r"/event/E-20\d{6}-\d{4}/[a-z0-9%_-]+",path.path):
            continue
        m=re.search(r"/event/E-(20\d{6})-",path.path)
        if not m:continue
        try:date=dt.datetime.strptime(m.group(1),"%Y%m%d").date()
        except ValueError:continue
        urls.append((u,date))
    return urls

def extract_factual_event(html,url,today,places,norm,category):
    soup=BeautifulSoup(html,"html.parser")
    title_el=soup.select_one("h1.event-detail__title")
    if not title_el:return None
    title=" ".join(title_el.get_text(" ",strip=True).split())[:175]
    if len(title)<6 or title.lower() in ("event not found","evento no encontrado"):return None

    texts=[" ".join(el.get_text(" ",strip=True).split()) for el in soup.select(".event-detail__details-list p.event-detail__text")]
    muni_by_norm={norm(key):key for key in places}
    muni=None
    for t in texts:
        k=norm(t)
        if k in muni_by_norm:
            muni=muni_by_norm[k]
            break
    if not muni:return None

    # Use actual visible date and time; JSON-LD often omits the start hour.
    start_day=None
    end_day=None
    start_time=None
    end_time=None
    for t in texts:
        if re.fullmatch(r"\d{2}/\d{2}/20\d{2}(?:\s*-\s*\d{2}/\d{2}/20\d{2})?",t):
            dates=re.findall(r"(\d{2})/(\d{2})/(20\d{2})",t)
            try:
                day,month,year=map(int,dates[0])
                start_day=dt.date(year,month,day)
                d2,m2,y2=map(int,dates[-1])
                end_day=dt.date(y2,m2,d2)
            except (IndexError,ValueError):pass
        mt=re.fullmatch(r"([0-2]\d:[0-5]\d)\s*-\s*([0-2]\d:[0-5]\d)",t)
        if mt:start_time,end_time=mt.groups()

    if not start_day:return None
    final_day=end_day or start_day
    if final_day<today or start_day>today+dt.timedelta(days=MAX_LOOKAHEAD_DAYS):
        return None
    if start_day<today-dt.timedelta(days=90):return None
    # Treat 00:00 and absent time as UNKNOWN, not as a midnight opening hour.
    # A range describes the published programme period, not confirmed daily sessions.
    known_time=bool(start_time and start_time!="00:00")
    if final_day>start_day:
        known_time=False
    venue=""
    for idx,t in enumerate(texts):
        if norm(t)==norm(muni) and idx>0:
            candidate=texts[idx-1]
            if not re.fullmatch(r"\d{2}/\d{2}/20\d{2}",candidate):
                venue=candidate[:160]
            break
    facts=source_facts.enhance(soup,muni,norm,final_day>start_day)
    venue=facts["venue"] or venue or "Consultar el recinto en la ficha oficial"

    status="approved"
    for tag in soup.select('script[type="application/ld+json"]'):
        try:ld=json.loads(tag.string or tag.get_text())
        except (TypeError,ValueError):continue
        nodes=ld if isinstance(ld,list) else [ld]
        for node in nodes:
            if isinstance(node,dict) and node.get("@type")=="Event" and str(node.get("eventStatus","")).endswith("EventCancelled"):
                status="cancelled"
    image=official_page_image(soup,url)
    return dict(
      **image_fields(image,title,SOURCE_NAME),
      title=title,start=start_day.isoformat()+("T"+start_time+":00" if known_time else ""),
      end=(final_day.isoformat() if final_day>start_day else
           (start_day.isoformat()+"T"+end_time+":00") if known_time and end_time and end_time>start_time else None),
      municipality=muni,venue=venue,category=category(title),
      free=facts["free"],price=facts["price"],details=facts["details"],
      organizer_url=facts["organizer_url"],
      source_name=SOURCE_NAME,source_url=url,status=status)

def synchronize(conn, now, today, places, norm, category, upsert, max_pages=MAX_PAGES_PER_RUN):
    scan_allowed()
    sitemap=list_public_events()
    if len(sitemap)<25:
        raise RuntimeError("Too few events in official sitemap; source format may have changed")
    conn.execute("""CREATE TABLE IF NOT EXISTS cabildo_scans(
      url TEXT PRIMARY KEY, checked_at TEXT NOT NULL, outcome TEXT NOT NULL)""")
    scan_columns={row[1] for row in conn.execute("PRAGMA table_info(cabildo_scans)")}
    if "image_inspected" not in scan_columns:
        conn.execute("ALTER TABLE cabildo_scans ADD COLUMN image_inspected INTEGER NOT NULL DEFAULT 0")
    if "facts_inspected" not in scan_columns:
        conn.execute("ALTER TABLE cabildo_scans ADD COLUMN facts_inspected INTEGER NOT NULL DEFAULT 0")
    existing={r[0]:(r[1],r[2],r[3],r[4]) for r in
              conn.execute("SELECT url,checked_at,outcome,image_inspected,facts_inspected FROM cabildo_scans").fetchall()}
    # Backfill metadata on previously scanned pages, while preserving a modest
    # per-run request limit. Historical images are refreshed in the same pass.
    pending_facts={u for u,(_,outcome,_,facts) in existing.items()
                   if outcome=="valid" and not facts}
    pending_images={u for u,(_,outcome,img,_) in existing.items()
                    if outcome=="valid" and not img}
    # Index events with a start date up to 120d ahead, allowing recently started multi-day
    # activities to be detected (but still refusing to invent session dates).
    candidates=[(u,d) for u,d in sitemap if today-dt.timedelta(days=45)<=d<=today+dt.timedelta(days=MAX_LOOKAHEAD_DAYS)]
    candidates.sort(key=lambda el:(el[0] not in pending_facts and el[0] not in pending_images,
                                   el[0] in existing, abs((el[1]-today).days), el[0]))
    # A zero-scan cycle is normal when every indexed page was recently checked.
    # Keep due and skipped counts separate so monitoring does not report an
    # idle but healthy connector as an extraction failure.
    refresh_candidates=[]
    skipped_recent=0
    for url,day in candidates:
        last=existing.get(url)
        if last:
            try:age=(dt.datetime.fromisoformat(now)-dt.datetime.fromisoformat(last[0])).total_seconds()
            except (TypeError,ValueError):age=9999999
            if age<2*86400 and url not in pending_images and url not in pending_facts:
                skipped_recent+=1
                continue
        refresh_candidates.append((url,day))
    add=changed=found=checked=0
    errors=[]
    for url,_ in refresh_candidates[:max_pages]:
        checked+=1
        try:
            r=SESSION.get(url,timeout=20,allow_redirects=False)
            if r.status_code in (429,500,502,503):
                errors.append(f"HTTP {r.status_code} - scan paused")
                break
            r.raise_for_status()
            if len(r.content)>400_000 or "text/html" not in r.headers.get("content-type",""):
                raise ValueError("Unexpected response")
            e=extract_factual_event(r.content,url,today,places,norm,category)
            if e:
                action=upsert(conn,e);found+=1
                add+=int(action=="added");changed+=int(action=="changed")
                outcome="valid"
            else:outcome="incomplete_or_out_of_window"
        except (requests.RequestException,ValueError) as exc:
            outcome="failed"
            errors.append(type(exc).__name__)
        conn.execute("""INSERT INTO cabildo_scans(url,checked_at,outcome,image_inspected,facts_inspected) VALUES(?,?,?,1,?)
          ON CONFLICT(url) DO UPDATE SET checked_at=excluded.checked_at,outcome=excluded.outcome,
            image_inspected=1,facts_inspected=excluded.facts_inspected""",
            (url,now,outcome,0 if outcome=="failed" else 1))
        # Never aggressively crawl: one page every ~0.65 s maximum
        time.sleep(0.65)
    conn.commit()
    return {"source":SOURCE_NAME,"checked_at":now,"found":found,"added":add,
            "changed":changed,"scanned":checked,"sitemap_count":len(sitemap),
            "eligible_urls":len(candidates),"due_urls":len(refresh_candidates),
            "skipped_recent":skipped_recent,
            "queued_remaining":max(0,len(refresh_candidates)-checked),
            "refresh_interval_hours":48,"error":"; ".join(errors[:3])}
