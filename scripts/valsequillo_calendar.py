"""First-party Valsequillo public municipal Google Calendar (ICS).

The link is prominently embedded by Ayuntamiento de Valsequillo and
has the municipal description. ICS is a structured source: parse only
explicit future, non-recurring entries with a named venue. Do NOT
relabel administrative appointments as entertainment, fabricate dates,
or interpret long-lived historic repeat RRULEs.
"""
import datetime as dt
import re
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo
import requests

NAME="Ayuntamiento de Valsequillo · calendario municipal"
MUNICIPALITY="Valsequillo"
ICS=("https://calendar.google.com/calendar/ical/"
     "valsequillogc.net_rlgn69gj2d455ot3m9p5v24tas%40group.calendar.google.com/public/basic.ics")
PAGE="https://www.valsequillogc.es/ayto3/calendario-de-eventos/"
HEADERS={"User-Agent":"CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"}
CANARY=ZoneInfo("Atlantic/Canary")
MAX_SIZE=3_000_000
MAX_ITEMS=4500
SKIP_ADMIN=re.compile(r"\b(?:dni|pasaporte|polic[ií]a nacional|renovaci[oó]n de documentos|padr[oó]n)\b",re.I)

def unfold(raw):
    lines=raw.replace("\r\n","\n").replace("\r","\n").split("\n")
    flattened=[]
    for line in lines:
        if line.startswith((" ","\t")) and flattened:
            flattened[-1]+=line[1:]
        else:flattened.append(line)
    return flattened

def unescape(text):
    return (text.replace(r"\n"," ").replace(r"\N"," ")
                .replace(r"\,",",").replace(r"\;",";")
                .replace(r"\\", "\\")).strip()

def parse_date(key,val):
    if not re.fullmatch(r"\d{8}(T\d{6}Z?)?",val):return None
    fmt="%Y%m%dT%H%M%SZ" if val.endswith("Z") else ("%Y%m%dT%H%M%S" if "T" in val else "%Y%m%d")
    stamp=dt.datetime.strptime(val,fmt)
    if val.endswith("Z"):
        return stamp.replace(tzinfo=dt.timezone.utc).astimezone(CANARY)
    if "T" not in val:return dt.date(stamp.year,stamp.month,stamp.day)
    # ONLY support the timezone explicitly linked in the public calendar.
    if "TZID=Atlantic/Canary" not in key:return None
    return stamp.replace(tzinfo=CANARY)

def parse_ical(text,today):
    if len(text)>MAX_SIZE or not text.startswith("BEGIN:VCALENDAR"):
        raise ValueError("Invalid municipal ICS or oversized source")
    if "X-WR-CALNAME:ACTIVIDADES MUNICIPALES" not in text:
        raise ValueError("Incorrect Valsequillo calendar identity")
    entries=[]
    current=None
    count=0
    for line in unfold(text):
        if line=="BEGIN:VEVENT":
            count+=1
            if count>MAX_ITEMS:raise ValueError("Unbounded municipal calendar")
            current={}
            continue
        if line=="END:VEVENT":
            if current is not None:entries.append(current)
            current=None
            continue
        if current is not None and ":" in line:
            key,value=line.split(":",1)
            current[key]=value
    result=[]
    for e in entries:
        if e.get("STATUS","CONFIRMED")!="CONFIRMED" or "RRULE" in e or "RECURRENCE-ID" in e:
            continue
        key=next((key for key in e if key=="DTSTART" or key.startswith("DTSTART;")),None)
        if not key:continue
        date=parse_date(key,e[key])
        if date is None:continue
        day=date.date() if isinstance(date,dt.datetime) else date
        if day<today or day>today+dt.timedelta(days=120):
            continue
        summary=unescape(e.get("SUMMARY",""))
        place=unescape(e.get("LOCATION",""))
        if (len(summary)<8 or len(summary)>150 or not place
            or SKIP_ADMIN.search(summary)
            or "Valsequillo" not in place):
            continue
        venue=place.split(",")[0].strip()
        if len(venue)<12 or "Valsequillo" in venue and venue.casefold()==MUNICIPALITY.casefold():
            continue
        start=day.isoformat()
        if isinstance(date,dt.datetime):
            start+="T"+date.strftime("%H:%M:%S")
        detail=unescape(e.get("DESCRIPTION",""))[:380]
        result.append({
            "title":summary,"start":start,"end":None,
            "municipality":MUNICIPALITY,"venue":venue,
            "category":"cultura","free":None,"price":"",
            "details":(detail+" " if detail else "")+"Calendario público municipal; consulta la fuente antes de asistir.",
            "source_name":NAME,"source_url":PAGE,
            "status":"approved"})
    unique={(x["title"].casefold(),x["start"]):x for x in result}
    return list(unique.values()),{"calendar_total":count,"matching_future":len(unique)}

def fetch(session):
    r=session.get("https://calendar.google.com/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if r.status_code not in (200,404,410):raise RuntimeError("Calendar robots status unavailable")
    policy=RobotFileParser()
    if r.status_code==200:policy.parse(r.text.splitlines())
    else:policy.allow_all=True
    if not policy.can_fetch(HEADERS["User-Agent"],ICS):
        raise PermissionError("Calendar disallows ICS")
    res=session.get(ICS,headers=HEADERS,timeout=26,allow_redirects=False,stream=True)
    if res.status_code!=200 or "text/calendar" not in res.headers.get("content-type",""):
        raise RuntimeError("Public municipal calendar unavailable")
    body=bytearray()
    for chunk in res.iter_content(65536):
        body.extend(chunk)
        if len(body)>MAX_SIZE:raise ValueError("Calendar too large")
    return body.decode("utf8")

# Manually verified from the public ICS linked in the municipal website
# on 29 Oct 2026. Google Calendar robots.txt explicitly Disallow: /;
# no scheduled fetch is permitted. No speculative recurrence.
SNAPSHOT=(
 {"title":"Circuito de narraci\u00f3n oral", "start":"2026-10-30T18:00:00",
  "venue":"Biblioteca Municipal Benito P?rez Gald?s de Valsequillo",
  "category":"cultura"},
)

def fetch_and_extract(today,places,session=None):
    if MUNICIPALITY not in places:return [],{"source":NAME,"found":0,"error":""}
    results=[]
    for e in SNAPSHOT:
        if not today<=dt.date.fromisoformat(e["start"][:10])<=today+dt.timedelta(days=120):continue
        results.append({**e,"end":None,"municipality":MUNICIPALITY,
             "free":None,"price":"",
             "details":"Actividad municipal en el calendario p?blico 2026, revisada manualmente. Comprueba la fuente antes de asistir.",
             "source_name":NAME,"source_url":PAGE,"status":"approved"})
    return results,{"source":NAME,"found":len(results),"error":"",
                    "method":"manually_verified_calendar_2026_no_bot_crawl"}
