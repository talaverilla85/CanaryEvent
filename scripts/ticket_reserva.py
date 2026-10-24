"""TuReservaOnline: bounded public listings and factual Gran Canaria event enrichment.

Only venue/date/lowest listed tariff and links are read from the public
front-end's own API. No buyer information, capacity, seller data or payment keys
are accessed or persisted. We do not interact with bookings or checkout.
"""
from __future__ import annotations
import datetime as dt
import re
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from decimal import Decimal, InvalidOperation
import requests

BASE="https://www.tureservaonline.es"
NAME="TuReservaOnline · agenda de Gran Canaria"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT,"Accept":"application/json"}
LIST_PAGE_SIZE=24
MAX_PAGES=6
GC_TOWNS={
 "ingenio":"Ingenio","aguimes":"Agüimes","arucas":"Arucas",
 "telde":"Telde","teror":"Teror","galdar":"Gáldar","moya":"Moya",
 "villa-de-moya":"Moya","agaete":"Agaete",
 "santa-maria-de-guia":"Santa María de Guía",
 "santa-maria-de-guia-de-gran-canaria":"Santa María de Guía",
 "las-palmas-de-g-c":"Las Palmas de Gran Canaria",
 "las-palmas-de-gran-canaria":"Las Palmas de Gran Canaria",
 "san-bartolome-de-tirajana":"San Bartolomé de Tirajana",
 "maspalomas":"San Bartolomé de Tirajana",
 "mogán":"Mogán","mogan":"Mogán","valleseco":"Valleseco",
 "valsequillo":"Valsequillo","firgas":"Firgas","artenara":"Artenara",
 "vega-de-san-mateo":"Vega de San Mateo",
 "santa-brigida":"Santa Brígida",
 "santa-lucia-de-tirajana":"Santa Lucía de Tirajana",
 "vecindario":"Santa Lucía de Tirajana",
 "teatro-victor-jara-vecindario":"Santa Lucía de Tirajana",
 "la-aldea-de-san-nicolas":"La Aldea de San Nicolás",
}

def robots_allowed(client, endpoint):
    """The site explicitly permits these public read-only paths for our agent."""
    r=client.get(BASE+"/robots.txt",timeout=12,headers=HEADERS)
    if r.status_code!=200:raise RuntimeError("TuReservaOnline robots policy unavailable")
    rp=RobotFileParser();rp.parse(r.text.splitlines())
    if not rp.can_fetch(AGENT,BASE+endpoint):
        raise PermissionError("TuReservaOnline disallows public event API read")

def fetch_listings(client=requests, pages=MAX_PAGES):
    endpoint="/api/active-events"
    robots_allowed(client,endpoint)
    items=[]
    for page in range(1,max(1,min(int(pages),MAX_PAGES))+1):
        path=f"/api/active-events?pageSize={LIST_PAGE_SIZE}&pageNumber={page}"
        r=client.get(BASE+path,timeout=18,headers=HEADERS,allow_redirects=False)
        if r.status_code in (403,429,500,502,503):raise RuntimeError(f"Ticket platform paused or refused requests: HTTP {r.status_code}")
        r.raise_for_status()
        if len(r.content)>600_000:raise ValueError("Unexpected listing response size")
        payload=r.json()
        data=payload.get("data") if isinstance(payload,dict) else None
        batch=data.get("items") if isinstance(data,dict) else None
        if not isinstance(batch,list):raise ValueError("Ticket platform listing format changed")
        items.extend(batch[:LIST_PAGE_SIZE])
        if len(batch)<LIST_PAGE_SIZE or len(items)>=int(data.get("total") or 0):break
        time.sleep(0.3)
    return items

def extract(entry, today, places, norm, category):
    if not isinstance(entry,dict) or entry.get("is_cancelled") is True:return None
    raw_town=str(entry.get("town") or "").strip()
    municipality=GC_TOWNS.get(norm(raw_town))
    if not municipality or municipality not in places:return None

    slug=entry.get("slug")
    if not isinstance(slug,str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,100}",slug):return None
    data_title=entry.get("title")
    title=(data_title.get("es") if isinstance(data_title,dict) else data_title)
    title=" ".join(str(title or "").split())[:180]
    if len(title)<5:return None
    raw_venue=entry.get("location")
    venue=(raw_venue.get("es") if isinstance(raw_venue,dict) else raw_venue)
    venue=" ".join(str(venue or "").split())[:170]
    if len(venue)<4:return None

    def parse_dt(value):
        if not isinstance(value,str):return None
        try:
            d=dt.datetime.strptime(value[:19],"%Y-%m-%d %H:%M:%S")
            return d
        except ValueError:return None
    beginning=parse_dt(entry.get("from")) or parse_dt(entry.get("date"))
    ending=parse_dt(entry.get("to")) or beginning
    if not beginning:return None
    if ending<beginning:ending=beginning
    if ending.date()<today or beginning.date()>today+dt.timedelta(days=180):return None
    # Do not fabricate sessions on each day of multi-date programmes.
    if ending.date()>beginning.date():
        start=beginning.date().isoformat()
        end=ending.date().isoformat()
        details="Actividad con varias fechas. Consulta el calendario de sesiones y la disponibilidad en la web de entradas."
    else:
        start=beginning.isoformat(timespec="seconds")
        end=ending.isoformat(timespec="seconds") if ending>beginning else None
        details="Información básica facilitada por la plataforma de entradas; consulta condiciones y posibles cambios en origen."
    if entry.get("is_sold_out") is True:
        details="Entradas agotadas según la plataforma. Consulta si hay cambios de disponibilidad."
    lowest=entry.get("lowest_fare")
    try:
        amount=Decimal(str(lowest))
        if not amount.is_finite() or amount<0 or amount>5000:amount=None
    except (TypeError,InvalidOperation):amount=None

    if entry.get("is_free") is True:
        price,free="Gratis",1
    elif amount is not None:
        formatted=str(int(amount)) if amount==int(amount) else format(amount.quantize(Decimal("0.01")),"f").replace(".",",")
        # 'desde' means a minimum tariff, NOT necessarily the final checkout cost.
        price,free=f"Desde {formatted} €",0
    else:price,free="",None

    image=entry.get("cover_image")
    if not isinstance(image,str):image=""
    parsed=urlsplit(image)
    if parsed.scheme!="https" or parsed.hostname!="www.tureservaonline.es" or not parsed.path.startswith("/storage/") or len(image)>600:
        image=""
    source_url=BASE+"/es/events/"+slug
    return dict(title=title,start=start,end=end,municipality=municipality,venue=venue,
       category=category(title),free=free,price=price,details=details,
       source_name=NAME,source_url=source_url,organizer_url="",
       image_url=image,image_alt=title if image else "",
       image_origin="TuReservaOnline" if image else "",
       image_status="official_remote" if image else "not_available",
       status="approved")

def reconcile(conn, entry, norm, now):
    """Update matching official entries, rather than creating duplicate ticket cards."""
    candidates=conn.execute("""SELECT * FROM events
      WHERE municipality=? AND substr(start,1,10)=? AND status='approved'""",
      (entry["municipality"],entry["start"][:10])).fetchall()
    new_name=norm(entry["title"])
    matched=[]
    for row in candidates:
        if norm(row["title"])==new_name:
            matched.append(row)
    if not matched:return (0,0)
    updated=0
    for row in matched:
        updates={}
        if entry["venue"] and (not row["venue"] or row["venue"].lower().startswith("consultar")):
            updates["venue"]=entry["venue"]
        if entry["price"] and (not row["price"] or row["free"] is None):
            updates["price"]=entry["price"]
            updates["free"]=entry["free"]
        if len(row["start"])==10 and len(entry["start"])>10:
            updates["start"]=entry["start"]
            updates["end"]=entry["end"]
        if not row["image_url"] and entry["image_url"]:
            for k in ("image_url","image_alt","image_origin","image_status"):updates[k]=entry[k]
        if not row["organizer_url"] or row["organizer_url"].startswith("https://ingenio.es/"):
            updates["organizer_url"]=entry["source_url"]
        if updates:
            updated+=1
            setters=",".join('"'+k+'"=?' for k in updates)
            conn.execute("UPDATE events SET "+setters+",updated_at=?,last_seen=? WHERE id=?",
                tuple(updates.values())+(now,now,row["id"]))
    return len(matched),updated

def synchronize(conn, now, today, places, norm, category, upsert,client=requests,pages=MAX_PAGES):
    listings=fetch_listings(client,pages=pages)
    found=added=changed=skipped=0
    seen=set()
    for item in listings:
        e=extract(item,today,places,norm,category)
        if not e:skipped+=1;continue
        key=(norm(e["title"]),e["municipality"],e["start"][:10])
        if key in seen:continue
        seen.add(key)
        found+=1
        matched,actual_changes=reconcile(conn,e,norm,now)
        if matched:
            changed+=actual_changes
        else:
            state=upsert(conn,e)
            added+=int(state=="added")
            changed+=int(state=="changed")
    conn.commit()
    return {"source":NAME,"checked_at":now,"found":found,"added":added,"changed":changed,"skipped_other_islands_or_expired":skipped,"error":""}
