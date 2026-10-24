"""Selective verification for a recently concluded event in the public ticket catalogue.

The listing API only includes *currently available* events. Verify a few
same-day catalogue records against exact event pages indexed by the provider.
Never touch users, providers, checkout or payment credentials in the response.
"""
from __future__ import annotations
import datetime as dt
import xml.etree.ElementTree as ET
import re
import time
from decimal import Decimal,InvalidOperation
import requests
from urllib.parse import urlsplit
import ticket_reserva as tr

def price_from_public_fares(data):
    if data.get("is_free") is True:return "Gratis",1
    raw=data.get("fares")
    amounts=[]
    if isinstance(raw,list):
        for item in raw:
            if not isinstance(item,dict) or item.get("published") not in (True,1):continue
            try:
                val=Decimal(str(item.get("price")))
                if val.is_finite() and 0<=val<=5000:amounts.append(val)
            except (InvalidOperation,TypeError):pass
    if amounts and all(x==0 for x in amounts):return "Gratis",1
    if amounts:
        low=min(amounts)
        text=str(int(low)) if low==int(low) else str(low.quantize(Decimal(".01"))).replace(".",",")
        return f"Desde {text} €",0
    return "",None

def fetch_single(client,slug):
    url=tr.BASE+"/api/events/"+slug
    response=client.get(url,timeout=15,headers=tr.HEADERS,allow_redirects=False)
    response.raise_for_status()
    if len(response.content)>140_000:raise ValueError("Detail payload oversize")
    data=response.json()
    if not isinstance(data,dict):raise ValueError("Unexpected ticket detail format")
    # Only return a deliberately minimal projection. Never retain/log seller payloads.
    name=data.get("lang_title")
    town=data.get("town")
    town=town.get("name") if isinstance(town,dict) else ""
    location=data.get("location")
    venue=location.get("lang_name") if isinstance(location,dict) else ""
    date=data.get("date")
    fares=data.get("fares")
    price,free=price_from_public_fares({"fares":fares,"is_free":data.get("is_free")})
    cover=data.get("coverimage") or {}
    images=cover.get("original") if isinstance(cover,dict) else []
    image=images[0].get("url","") if isinstance(images,list) and images and isinstance(images[0],dict) else ""
    try:
        parsed=urlsplit(image)
        if parsed.scheme!="https" or parsed.hostname!="www.tureservaonline.es" or not parsed.path.startswith("/storage/"):
            image=""
    except ValueError:image=""
    return dict(title=name,town=town,venue=venue,date=date,price=price,free=free,
                image=image,cancelled=data.get("is_cancelled") in (True,1))

def reconcile_recent(conn,now,today,places,norm,client=requests,max_details=4):
    # Exact-match indexed URLs avoid guessing an event page from its title.
    tr.robots_allowed(client,"/sitemap.xml")
    tr.robots_allowed(client,"/api/events/")
    resp=client.get(tr.BASE+"/sitemap.xml",timeout=18,headers=tr.HEADERS,allow_redirects=False)
    resp.raise_for_status()
    if len(resp.content)>600_000:raise ValueError("Ticket sitemap too large")
    tree=ET.fromstring(resp.content)
    known_slugs=set()
    for x in tree.findall(".//{*}loc"):
        if not x.text:continue
        url=urlsplit(x.text)
        if url.scheme!="https" or url.hostname!="www.tureservaonline.es":continue
        match=re.fullmatch(r"/es/events/([a-z0-9][a-z0-9_-]{2,100})",url.path)
        if match:known_slugs.add(match.group(1))
    conn.execute("""CREATE TABLE IF NOT EXISTS ticket_recent_checks(
        slug TEXT PRIMARY KEY, checked_at TEXT NOT NULL)""")
    recent_start=(today-dt.timedelta(days=1)).isoformat()
    recent_end=(today+dt.timedelta(days=2)).isoformat()
    rows=conn.execute("""SELECT * FROM events WHERE substr(start,1,10)>=? AND substr(start,1,10)<=?
                         AND status='approved' AND (price='' OR venue LIKE 'Consultar%')""",(recent_start,recent_end)).fetchall()
    candidates={}
    for row in rows:
        if row["source_name"].startswith("TuReservaOnline"):continue
        slug=norm(row["title"])
        if slug in known_slugs:
            candidates.setdefault(slug,[]).append(row)
    changed=checked=0
    for slug,records in candidates.items():
        if checked>=max_details:break
        old=conn.execute("SELECT checked_at FROM ticket_recent_checks WHERE slug=?",(slug,)).fetchone()
        if old:
            try:
                if (dt.datetime.fromisoformat(now)-dt.datetime.fromisoformat(old[0])).total_seconds()<36*3600:continue
            except (TypeError,ValueError):pass
        checked+=1
        try:
            detail=fetch_single(client,slug)
            if detail["cancelled"]:continue
            town=tr.GC_TOWNS.get(norm(detail["town"]))
            if not town or town not in places:continue
            if norm(detail["title"])!=slug:continue
            try:date=dt.datetime.strptime(str(detail["date"]),"%d-%m-%Y %H:%M")
            except ValueError:continue
            for row in records:
                if row["start"][:10]!=date.date().isoformat():continue
                if row["municipality"]!=town:
                    # Fix a known class of bad Cabildo municipal tags, only when
                    # the official source it links to is already a matching card
                    # in the same actual municipality and date.
                    if row["source_name"].startswith("Portal oficial de Eventos Gran Canaria"):
                        src=row["organizer_url"] or ""
                        direct=conn.execute("""SELECT id,title,source_name,source_url,organizer_url
                            FROM events WHERE municipality=? AND substr(start,1,10)=?
                                  AND status='approved'""",(town,date.date().isoformat())).fetchall()
                        # Require a separate trusted municipal record, same title/day,
                        # and either its original URL is the Cabildo reference, or
                        # that ticket page is attached to the municipal record.
                        for candidate in direct:
                            if norm(candidate["title"])!=slug:continue
                            references_original=candidate["source_url"]==src
                            municipal_title=(norm(candidate["source_name"]).startswith("ayuntamiento-de-"+norm(town)))
                            ticket_verified=(candidate["organizer_url"]==tr.BASE+"/es/events/"+slug)
                            source_host=urlsplit(src).hostname
                            trusted_link=(source_host in ("ingenio.es","www.ingenio.es"))
                            if not (references_original or municipal_title and ticket_verified and trusted_link):
                                continue
                            conn.execute("UPDATE events SET status='duplicate',updated_at=? WHERE id=?",
                                         (now,row["id"]))
                            changed+=1
                            break
                    continue
                updates={}
                if detail["venue"] and row["venue"].lower().startswith("consultar"):
                    updates["venue"]=str(detail["venue"])[:160]
                if detail["price"] and not row["price"]:
                    updates["price"]=detail["price"];updates["free"]=detail["free"]
                if len(row["start"])==10:updates["start"]=date.isoformat(timespec="seconds")
                if not row["organizer_url"] or row["organizer_url"].startswith("https://ingenio.es/"):
                    updates["organizer_url"]=tr.BASE+"/es/events/"+slug
                if not row["image_url"] and detail["image"]:
                    updates.update(image_url=detail["image"],image_alt=row["title"],image_origin="TuReservaOnline",
                                   image_status="official_remote")
                if updates:
                    columns=",".join('"'+k+'"=?' for k in updates)
                    conn.execute("UPDATE events SET "+columns+",updated_at=?,last_seen=? WHERE id=?",
                        tuple(updates.values())+(now,now,row["id"]))
                    changed+=1
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            print(f"INFO ticket recent detail unavailable: {type(exc).__name__}")
        finally:
            conn.execute("""INSERT INTO ticket_recent_checks(slug,checked_at) VALUES(?,?)
                ON CONFLICT(slug) DO UPDATE SET checked_at=excluded.checked_at""",(slug,now))
            time.sleep(0.35)
    conn.commit()
    return {"examined":checked,"enriched":changed}
