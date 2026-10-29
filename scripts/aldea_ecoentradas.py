"""Upcoming La Aldea theatre events from venue-specific EcoEntradas listing.

This is NOT a direct Ayuntamiento feed: it is an independent original
ticket outlet, used because the municipality's HTTPS TLS trust fails.
Verify exact original hall by venue listing + session row + zone page,
including 2-digit year. Do not infer a year from a poster's month alone.
No scraping seat availability or purchase interactions.
"""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import requests

NAME="EcoEntradas · Centro Municipal de Cultura de La Aldea"
ROOT="https://www.ecoentradas.com"
LISTING=ROOT+"/ver-recinto/132"
VENUE="Centro Municipal de Cultura la Aldea"
MUNICIPALITY="La Aldea de San Nicolás"
HEADERS={"User-Agent":"CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)","Accept":"text/html"}
UA=HEADERS["User-Agent"]
MAX_EVENTS=8
MAX_SESSIONS=15
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}

def valid_page(url,kind):
    try:
        part=urlsplit(str(url or ""))
        return (part.scheme=="https" and part.hostname=="www.ecoentradas.com"
                and part.port in (None,443) and not part.username and not part.password
                and not part.query and not part.fragment
                and bool(re.fullmatch(r"/"+kind+r"/[1-9]\d{0,9}",part.path)))
    except (ValueError,TypeError):return False

def robots(session):
    response=session.get(ROOT+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if response.status_code not in (200,404,410):
        raise RuntimeError("EcoEntradas robots unavailable")
    rp=RobotFileParser()
    if response.status_code==200:rp.parse(response.text.splitlines())
    else:rp.allow_all=True
    return rp

def get_html(session,url,policy):
    if not policy.can_fetch(UA,url):
        raise PermissionError("EcoEntradas robots disallow URL")
    response=session.get(url,headers=HEADERS,timeout=18,allow_redirects=False)
    if response.status_code!=200 or len(response.content)>1_300_000:
        raise RuntimeError("EcoEntradas source unavailable")
    if "html" not in response.headers.get("Content-Type","text/html"):
        raise ValueError("EcoEntradas source not HTML")
    return BeautifulSoup(response.content,"html.parser")

def session_links(soup):
    header=soup.select_one("h1")
    text=header.get_text(" ",strip=True) if header else ""
    if text.casefold()!=VENUE.casefold():
        raise ValueError("EcoEntradas listing is not expected hall")
    place=soup.get_text(" ",strip=True)
    if "Gran Canaria" not in place or "La Aldea" not in place:
        raise ValueError("EcoEntradas listing has wrong town or island")
    links=[]
    for a in soup.select('a[href]'):
        url=a.get("href","")
        if valid_page(url,"elegirsesion") and url not in links:
            links.append(url)
    if len(links)>MAX_EVENTS:
        raise ValueError("Too many EcoEntradas events for bounded verification")
    return links

def parse_sessions(soup):
    title=soup.select_one("h1")
    if title is None:return "",[]
    title=title.get_text(" ",strip=True)
    if len(title)<5 or len(title)>140:return "",[]
    rows=[]
    for tr in soup.select("tr"):
        day=tr.select_one(".day")
        month=tr.select_one(".month")
        dateandplace=tr.select_one(".dates")
        price=tr.select_one(".price-sesion")
        link=next((a.get("href","") for a in tr.select("a[href]")
                   if valid_page(a.get("href",""),"elegirzona")),None)
        if not (day and month and dateandplace and link):
            continue
        if not day.get_text(" ",strip=True).isdigit():continue
        d=int(day.get_text(" ",strip=True))
        m=MONTHS.get(month.get_text(" ",strip=True).lower())
        if not m or not 1<=d<=31:continue
        detail=dateandplace.get_text(" ",strip=True)
        clock=re.search(r"\b([01]\d|2[0-3]):([0-5]\d)\b",detail)
        if not clock or VENUE.casefold() not in detail.casefold():continue
        euro=""
        if price:
            pr=re.search(r"(\d{1,3})(?:[,.](\d{1,2}))?\s*\u20ac",
                         price.get_text(" ",strip=True))
            if pr:
                euro=pr.group(1)+("."+pr.group(2).ljust(2,"0") if pr.group(2) else "")
        if not euro:continue  # price must be explicit, not assumed
        rows.append({"month":m,"day":d,"clock":clock.group(0),"url":link,
                     "price":euro})
    return title,rows

def verified_zone(soup,title,item):
    h1=soup.select_one("h1")
    if not h1 or h1.get_text(" ",strip=True).casefold()!=title.casefold():
        return None
    # Visible zone header: "En La Aldea // Centro Municipal ... // 14-11-26 // 20:00"
    intro=soup.get_text(" ",strip=True)[:800]
    pattern=(re.escape(VENUE)+r"\s*//\s*(\d{1,2})-(\d{2})-(\d{2})"
             +r"\s*//\s*([01]\d|2[0-3]):([0-5]\d)")
    m=re.search(pattern,intro,re.I)
    if not m or "En La Aldea de San Nicolás" not in intro:
        return None
    day=int(m.group(1));month=int(m.group(2));year=2000+int(m.group(3))
    try:date=dt.date(year,month,day)
    except ValueError:return None
    if (day,month)!=(item["day"],item["month"]) or m.group(4)+":"+m.group(5)!=item["clock"]:
        return None
    return date

def extract(session,today,category,places):
    if MUNICIPALITY not in places:return [],{"source":NAME,"found":0,"error":""}
    rp=robots(session)
    listing=get_html(session,LISTING,rp)
    links=session_links(listing)
    found=[]
    errors=[]
    checked=0
    for link in links:
        try:
            title,sessions=parse_sessions(get_html(session,link,rp))
            if len(sessions)>MAX_SESSIONS:raise ValueError("Too many sessions")
            for item in sessions:
                zone=get_html(session,item["url"],rp)
                date=verified_zone(zone,title,item)
                if not date or not today<=date<=today+dt.timedelta(days=120):
                    continue
                start=date.isoformat()+"T"+item["clock"]+":00"
                found.append({
                    "title":title,"start":start,"end":None,
                    "municipality":MUNICIPALITY,"venue":VENUE,
                    "category":category(title) if category(title)!="ocio" else "cultura","free":0,
                    "price":"Desde "+(item["price"].rstrip("0").rstrip(".") if "." in item["price"] else item["price"])+" \u20ac",
                    "details":"Entrada de pago, precio inicial según EcoEntradas. Confirma condiciones y disponibilidad en la taquilla.",
                    "source_name":NAME,"source_url":link,
                    "organizer_url":link,"status":"approved"})
                checked+=1
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
            errors.append(type(exc).__name__)
    uniq={entry["title"].casefold()+"|"+entry["start"]:entry for entry in found}
    report={"source":NAME,"found":len(uniq),"added":0,"changed":0,
            "venues_checked":1,"links_checked":len(links),
            "sessions_verified":checked,
            "error":"; ".join(errors)[:180]}
    return list(uniq.values()),report

def fetch_and_extract(today,places,category,session=None):
    return extract(session or requests.Session(),today,category,places)
