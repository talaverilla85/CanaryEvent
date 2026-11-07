"""La Aldea cultural hall events from EcoEntradas' public event pages.

As of Nov 2026, www.ecoentradas.com redirects to ecoentradas.com and the
ticket/seat-selection URL /elegirzona/ is explicitly disallowed by robots.txt.
Use ONLY the public hall listing and /eventos/<slug>-YYYY-MM-DD detail pages.
The public Event JSON-LD independently confirms date, time, named hall and
price. Never crawl seat maps, checkout, ticket availability or blocked URLs.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

NAME="EcoEntradas · Centro Municipal de Cultura de La Aldea"
ROOT="https://ecoentradas.com"
LISTING=ROOT+"/recintos/centro-municipal-de-cultura-la-aldea"
VENUE="Centro Municipal de Cultura la Aldea"
MUNICIPALITY="La Aldea de San Nicolás"
HEADERS={
    "User-Agent":"CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)",
    "Accept":"text/html,application/xhtml+xml",
}
UA=HEADERS["User-Agent"]
MAX_EVENTS=8
MAX_BYTES=1_300_000
EVENT_PATH=re.compile(r"/eventos/[a-z0-9-]+-(20\d{2}-\d{2}-\d{2})$",re.I)
START=re.compile(r"^(20\d{2}-\d{2}-\d{2})T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)"
                 r"(?:Z|[+-][01]\d:[0-5]\d)$")
POSTER=re.compile(r"/cartel/[A-Za-z0-9_-]{4,60}/[A-Za-z0-9._%-]+\.(?:jpg|jpeg|png|webp|avif)$",re.I)


def public_url(value,kind="event"):
    """Strict allowlist excludes www redirects, checkout and arbitrary hosts."""
    try:
        part=urlsplit(str(value or ""))
        if (part.scheme!="https" or part.hostname!="ecoentradas.com"
            or part.port not in (None,443) or part.username or part.password
            or part.query or part.fragment):
            return False
        return (bool(EVENT_PATH.fullmatch(part.path))
                if kind=="event" else part.path==LISTING.removeprefix(ROOT))
    except (TypeError,ValueError):
        return False


def robots(session):
    response=session.get(ROOT+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if response.status_code not in (200,404,410):
        raise RuntimeError("EcoEntradas robots unavailable (HTTP "+str(response.status_code)+")")
    rp=RobotFileParser()
    if response.status_code==200:
        rp.parse(response.text.splitlines())
    else:
        rp.allow_all=True
    return rp


def get_html(session,url,policy):
    if not (public_url(url) or public_url(url,"listing")):
        raise ValueError("EcoEntradas public URL not allowlisted")
    if not policy.can_fetch(UA,url):
        raise PermissionError("EcoEntradas robots disallow URL")
    response=session.get(url,headers=HEADERS,timeout=18,allow_redirects=False)
    if response.status_code!=200:
        raise RuntimeError("EcoEntradas public page HTTP "+str(response.status_code))
    if len(response.content)>MAX_BYTES:
        raise ValueError("EcoEntradas response too large")
    if "html" not in response.headers.get("Content-Type","text/html").lower():
        raise ValueError("EcoEntradas source not HTML")
    return BeautifulSoup(response.content,"html.parser")


def public_links(soup):
    h1=soup.select_one("h1")
    if not h1 or h1.get_text(" ",strip=True).casefold()!=VENUE.casefold():
        raise ValueError("EcoEntradas listing is not expected hall")
    text=soup.get_text(" ",strip=True)
    if "Gran Canaria" not in text or "La Aldea" not in text:
        raise ValueError("EcoEntradas listing has wrong town or island")
    links=[]
    for link in soup.select('a[href*="/eventos/"]'):
        url=link.get("href","")
        if public_url(url) and url not in links:
            links.append(url)
    if len(links)>MAX_EVENTS:
        raise ValueError("Too many EcoEntradas events for bounded verification")
    return links


def event_record(soup,url,today,category):
    if not public_url(url):
        return None
    day_in_link=EVENT_PATH.fullmatch(urlsplit(url).path).group(1)
    h1=soup.select_one("h1")
    title=" ".join(h1.get_text(" ",strip=True).split()) if h1 else ""
    if not 5<=len(title)<=140:
        return None
    records=[]
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            value=json.loads(tag.string or tag.get_text())
        except (TypeError,ValueError):
            continue
        nodes=value if isinstance(value,list) else [value]
        for node in nodes:
            if isinstance(node,dict) and node.get("@type")=="Event":
                records.append(node)
    if len(records)!=1:
        return None
    data=records[0]
    if (data.get("url")!=url or (data.get("@id") and data["@id"]!=url)
        or str(data.get("eventStatus","")).split("/")[-1]!="EventScheduled"
        or not str(data.get("name","")).casefold().startswith(title.casefold())):
        return None
    stamp=str(data.get("startDate") or "")
    match=START.fullmatch(stamp)
    if not match or match.group(1)!=day_in_link:
        return None
    try:
        when=dt.date.fromisoformat(match.group(1))
    except ValueError:
        return None
    if not today<=when<=today+dt.timedelta(days=120):
        return None
    location=data.get("location")
    if not isinstance(location,dict) or str(location.get("name","")).casefold()!=VENUE.casefold():
        return None
    if location.get("url")!=LISTING:
        return None
    address=location.get("address")
    if not isinstance(address,dict):
        return None
    if ("Gran Canaria" not in str(address.get("addressLocality",""))
        or "La Aldea" not in str(address.get("streetAddress",""))):
        return None
    offer=data.get("offers")
    if not isinstance(offer,dict) or offer.get("priceCurrency")!="EUR":
        return None
    try:
        amount=Decimal(str(offer.get("price") or ""))
    except (InvalidOperation,ValueError):
        return None
    if not amount.is_finite() or not Decimal(0)<=amount<=Decimal(5000):
        return None
    label=format(amount.normalize(),"f")
    image=str(data.get("image") or "")
    image_parts=urlsplit(image)
    if not (image_parts.scheme=="https" and image_parts.hostname=="ecoentradas.com"
            and not image_parts.query and not image_parts.fragment
            and POSTER.fullmatch(image_parts.path)):
        image=""
    free=int(amount==0)
    start=when.isoformat()+"T"+match.group(2)+":"+match.group(3)+":00"
    kind=category(title)
    return {
        "title":title,"start":start,"end":None,
        "municipality":MUNICIPALITY,"venue":VENUE,
        "category":"cultura" if kind=="ocio" else kind,
        "free":free,"price":"Gratis" if free else "Desde "+label+" €",
        "details":"Función anunciada en EcoEntradas para el Centro Municipal de Cultura de La Aldea. Confirma las condiciones y posibles cambios en el enlace original.",
        "source_name":NAME,"source_url":url,"organizer_url":url,
        "status":"approved","image_url":image,
        "image_alt":title if image else "",
        "image_origin":"EcoEntradas · cartel oficial" if image else "",
        "image_status":"official_remote" if image else "not_available",
    }


def extract(session,today,category,places):
    if MUNICIPALITY not in places:
        return [],{"source":NAME,"found":0,"error":""}
    policy=robots(session)
    listing=get_html(session,LISTING,policy)
    links=public_links(listing)
    rows=[]
    errors=[]
    for url in links:
        try:
            event=event_record(get_html(session,url,policy),url,today,category)
            if event:
                rows.append(event)
            else:
                errors.append("Event evidence incomplete")
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
            errors.append(type(exc).__name__)
    unique={entry["title"].casefold()+"|"+entry["start"]:entry for entry in rows}
    report={"source":NAME,"found":len(unique),"added":0,"changed":0,
            "venues_checked":1,"links_checked":len(links),
            "sessions_verified":len(unique),"error":"; ".join(errors)[:180]}
    return list(unique.values()),report


def fetch_and_extract(today,places,category,session=None):
    return extract(session or requests.Session(),today,category,places)
