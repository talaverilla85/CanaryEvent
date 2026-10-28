"""Venue from the organizer's own precisely matched, structured programme.

Never infer a venue from organizer name, footer address, or a geolocation
centroid. Date-scoped school performances may have multiple actual locations;
accept exactly one location on the event's recorded day/time.
"""
from __future__ import annotations
import datetime as dt
import re
from urllib.parse import urlsplit

import venue_quality

SUPPORTED_HOSTS={"ofgrancanaria.com","lpacultura.com","casafrica.es","cultura.icdcultural.org"}

def host_of(url):
    host=(urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host

def _exact_place(candidate,municipality):
    text=" ".join(str(candidate or "").split()).strip(" -:;,")
    if len(text)>90 or len(text)<7:return ""
    if re.search(r"\d{1,3}\.\d{4,}",text):return ""  # GPS pasted into a venue name
    if not venue_quality.named_venue({"venue":text,"municipality":municipality}):return ""
    return text

def filarmonica(soup,municipality,event_day,event_time=""):
    entries=[]
    for element in soup.select(".event__information .event__show-container"):
        text=element.get_text(" ",strip=True)
        m=re.fullmatch(r"(\d{2})/(\d{2})/(20\d{2})\s*-\s*(\d{2}:\d{2})\s+(.+)",text)
        if not m:continue
        try:
            day=dt.date(int(m.group(3)),int(m.group(2)),int(m.group(1))).isoformat()
        except ValueError:continue
        if day!=event_day:continue
        if event_time and m.group(4)!=event_time:continue
        name=_exact_place(m.group(5),municipality)
        if name:entries.append(name)
    variants={venue_quality.norm(x):x for x in entries}
    return next(iter(variants.values())) if len(variants)==1 else ""

def lpacultura(soup,municipality):
    candidates=[]
    for x in soup.select(".event-show-title"):
        label=x.get_text(" ",strip=True)
        if label.casefold()!="lugar":continue
        parent=x.parent
        if not parent:continue
        direct=parent.find("a",href=re.compile(r"^https://(?:www\.)?lpacultura\.com/places/"))
        if not direct:continue
        href=direct.get("href","")
        # The linked named place is an exact, dedicated official venue page.
        if not re.fullmatch(r"https://(?:www\.)?lpacultura\.com/places/[a-z0-9-]+/?",href):continue
        name=_exact_place(direct.get_text(" ",strip=True),municipality)
        if name:candidates.append(name)
    variants={venue_quality.norm(x):x for x in candidates}
    return next(iter(variants.values())) if len(variants)==1 else ""

def casafrica(soup,municipality):
    candidates=[]
    for node in soup.select(".fw-bold"):
        if node.get_text(" ",strip=True).casefold()!="lugar:":continue
        nxt=node.find_next_sibling("div")
        if not nxt or "gray-dark" not in nxt.get("class",[]):continue
        # Only a first direct text node before the embedded map. Otherwise
        # the map's latitude/longitude gets appended to the location name.
        from bs4 import NavigableString
        values=[str(x).strip() for x in nxt.contents if isinstance(x,NavigableString) and str(x).strip()]
        if len(values)!=1:continue
        name=_exact_place(values[0],municipality)
        if name:candidates.append(name)
    variants={venue_quality.norm(x):x for x in candidates}
    return next(iter(variants.values())) if len(variants)==1 else ""

def icdcultural(soup,municipality,event_day,event_time=""):
    """Recognize explicit venue sentences on the event-specific Cultura page.

    The theatre can organize workshops elsewhere. An organizer, global map,
    footer address or a secondary mention of Teatro Guiniguada is not a
    venue. Require a matching official event DATE, starting HOUR (when
    known), and a sentence explicitly specifying where this event occurs.
    """
    if municipality!="Las Palmas de Gran Canaria":
        return ""
    try:
        day=dt.date.fromisoformat(event_day).strftime("%d/%m/%Y")
    except ValueError:
        return ""
    dates={node.get_text(" ",strip=True) for node in soup.select(".text-block-323")}
    if day not in dates:
        return ""
    paragraphs=soup.select(".div-block-527 .w-richtext p")
    if not paragraphs:
        return ""
    text=" ".join(p.get_text(" ",strip=True) for p in paragraphs)
    if event_time:
        # Explicit "Horario" means the source identifies the session,
        # not merely the date (which may recur with a different hall).
        hours=re.findall(r"\bHorario\s*:\s*([01]\d|2[0-3]):([0-5]\d)",text,re.I)
        if not hours or event_time not in {h+":"+m for h,m in hours}:
            return ""
    text=re.sub(r"\bSta\.\s+", "Santa ",text,flags=re.I)
    # Match one sentence of positive, event-specific venue attribution.
    # Never use incidental references to organizations or performers.
    patterns=(
       r"\bLa sede del (?:taller|curso|evento|encuentro|acto|concierto|espect[aá]culo) ser[aá] (?:el|la)\s+([^.!?]{9,120})",
       r"\b(?:El taller|La actividad|El encuentro|El concierto|El espect[aá]culo) (?:tendr[aá] lugar|se celebrar[aá]) en (?:el|la)\s+([^.!?]{9,120})",
    )
    names=[]
    for pattern in patterns:
        for m in re.finditer(pattern,text,re.I):
            candidate=m.group(1).strip(" .,:;()-")
            if not re.match(r"(?i)^(?:gimnasio|aulario|teatro|sala|auditorio|centro|biblioteca|plaza|pabell[oó]n|patio|sal[oó]n|campus|museo|casa|espacio|parque)\b",candidate):
                continue
            candidate=candidate[0].upper()+candidate[1:]
            name=_exact_place(candidate,municipality)
            if name:names.append(name)
    variants={venue_quality.norm(x):x for x in names}
    return next(iter(variants.values())) if len(variants)==1 else ""

def extract(soup,url,municipality,event_day,event_time=""):
    host=host_of(url)
    if host=="ofgrancanaria.com":
        return filarmonica(soup,municipality,event_day,event_time)
    if host=="lpacultura.com":
        return lpacultura(soup,municipality)
    if host=="casafrica.es":
        return casafrica(soup,municipality)
    if host=="cultura.icdcultural.org":
        return icdcultural(soup,municipality,event_day,event_time)
    return ""


def municipality_consistent(soup,url,municipality,venue):
    """Reject independent organizer locations outside the Cabildo municipality.

    A precise venue alone must not silently turn an event in Madrid/Paris/
    Agüimes into a plan in Las Palmas de Gran Canaria.
    """
    import unicodedata
    def norm(t):
        return "".join(ch for ch in unicodedata.normalize("NFKD",str(t).casefold())
                       if not unicodedata.combining(ch))
    named=norm(venue)
    mun=norm(municipality)
    if not venue or not venue_quality.named_venue({"venue":venue,"municipality":municipality}):
        return False
    for foreign in ("madrid","paris","parís","barcelona","tenerife","fuerteventura",
                    "lanzarote","la palma","la gomera","el hierro"):
        if foreign in named and foreign not in mun:
            return False
    for other in ("aguimes","arucas","galdar","teror","mogan","telde","ingenio",
                  "firgas","tejeda","artenara","valsequillo","valleseco","moya"):
        if other in named and other not in mun:
            return False
    if host_of(url)=="casafrica.es":
        points=[]
        for el in soup.select("[data-lat][data-lng]"):
            try:points.append((float(el["data-lat"]),float(el["data-lng"])))
            except (TypeError,ValueError):continue
        if points:
            # The municipal source says Las Palmas but another island, mainland
            # or different municipality must never be passed off as the capital.
            if municipality=="Las Palmas de Gran Canaria":
                return all(28.01<=lat<=28.24 and -15.58<=lon<=-15.34
                           for lat,lon in points)
            return all(27.70<=lat<=28.25 and -15.90<=lon<=-15.30
                       for lat,lon in points)
        # When the organizer has no map at all, only validated city institutions.
        return municipality=="Las Palmas de Gran Canaria" and norm(venue) in {
            "casa africa","casa de colon"
        }
    return True
