"""Reusable schema.org/Event importer for official Canary municipal EventON calendars.

Never infer a session from event descriptions or a festival date range.
Allowed first-party venue pages, one scheduled performance per explicit
startDate, approved exact name/venue, and verify source island + municipality.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
import venue_quality

SOURCES=(
 {"name":"Ayuntamiento de Agüimes · programación de teatros",
  "url":"https://aguimes.es/event-location/teatro-auditorio-aguimes/",
  "host":"aguimes.es","municipality":"Agüimes",
  "venues":{"Teatro Auditorio Agüimes"}},
 {"name":"Ayuntamiento de Agüimes · Teatro Cruce de Culturas",
  "url":"https://aguimes.es/event-location/teatro-cruce-de-culturas/",
  "host":"aguimes.es","municipality":"Agüimes",
  "venues":{"Teatro Cruce de Culturas"}},
 {"name":"Ayuntamiento de Gáldar · Centro Cultural Guaires",
  "url":"https://www.galdar.es/event-location/centro-cultural-guaires/",
  "host":"www.galdar.es","municipality":"Gáldar",
  "venues":{"Centro Cultural Guaires"}}
)
START_RE=re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2})")
ENDPOINT_RE=re.compile(r"^/events/[a-z0-9-]+/$",re.I)

def looks_official(url,host):
    try:
        p=urlsplit(url)
        return (p.scheme=="https" and p.hostname==host
                and p.port in (None,443) and p.username is None
                and p.password is None and not p.query and not p.fragment
                and bool(ENDPOINT_RE.fullmatch(p.path)))
    except (ValueError,TypeError):
        return False

def parse(soup,source,today):
    events=[]
    rejected=0
    seen=set()
    for card in soup.select(".eventon_list_event"):
        for tag in card.select('script[type="application/ld+json"]'):
            try:
                item=json.loads(tag.get_text(" ",strip=True))
            except (ValueError,TypeError):
                rejected+=1;continue
            if not isinstance(item,dict) or item.get("@type")!="Event":
                continue
            date_text=str(item.get("startDate") or "")
            m=START_RE.match(date_text)
            if not m:rejected+=1;continue
            try:
                day=dt.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
                hour=int(m.group(4));minute=int(m.group(5))
            except ValueError:
                rejected+=1;continue
            if hour>23 or minute>59 or not today<=day<=today+dt.timedelta(days=180):
                continue
            title=" ".join(str(item.get("name") or "").split())
            url=str(item.get("url") or "")
            location=item.get("location",{})
            if isinstance(location,list):
                location=location[0] if len(location)==1 else {}
            venue=" ".join(str(location.get("name") or "").split()) if isinstance(location,dict) else ""
            if (len(title)<6 or not looks_official(url,source["host"])
                or venue not in source["venues"] or
                not venue_quality.named_venue({"venue":venue,"municipality":source["municipality"]})
                or item.get("eventStatus","").endswith("EventCancelled")):
                rejected+=1;continue
            key=(url,day.isoformat(),hour,minute)
            if key in seen:continue
            seen.add(key)
            from bs4 import BeautifulSoup as BS
            details=BS(str(item.get("description") or ""),"html.parser").get_text(" ",strip=True)
            producer="Camino Viejo Producciones" if "camino viejo producciones" in details.lower() else ""
            # Producer is a credit, never a substitute for venue or date.
            category="familia" if any(w in title.lower() for w in ("blancanieves","musical infantil","infantil")) else "musica" if any(w in title.lower() for w in ("concierto","música","gofiones","cuerdas")) else "cultura"
            events.append({
                "title":title[:180],"start":f"{day.isoformat()}T{hour:02d}:{minute:02d}:00",
                "end":None,"municipality":source["municipality"],"venue":venue,
                "category":category,"free":None,"price":"",
                "details":(producer+" · Producción acreditada en la web municipal."
                           if producer else "Programación verificada en agenda municipal oficial."),
                "source_name":source["name"],"source_url":url,"status":"approved"
            })
    return events,{"cards":len(soup.select(".eventon_list_event")),"rejected":rejected}

def collect(today,fetch):
    all_events=[]
    outcomes=[]
    for source in SOURCES:
        try:
            soup=fetch(source["url"])
            events,stats=parse(soup,source,today)
            if not events:raise ValueError("No future official stage sessions parsed")
            all_events.extend(events)
            outcomes.append({"source":source["name"],"found":len(events),"error":"","stats":stats})
        except Exception as err:
            outcomes.append({"source":source["name"],"found":0,"error":type(err).__name__})
    return all_events,outcomes
