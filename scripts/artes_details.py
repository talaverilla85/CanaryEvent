"""Extract facts from the ORIGINAL Circuito de Artes Escénicas event detail pages.

Do not reuse large blocks of organizer-owned synopsis text. Short summaries are
assembled from a limited portion of the event description, with source linking.
"""
from __future__ import annotations
from datetime import datetime,timedelta
import re
import unicodedata
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString,Tag

HOST="artesescenicasgrancanaria.com"
SOURCE_PREFIX="https://artesescenicasgrancanaria.com/evento-"

def normalized(s):
    return unicodedata.normalize("NFKD",str(s)).casefold()

def fetch_detail(url,client=requests):
    p=urlparse(url)
    if p.scheme!="https" or p.hostname!=HOST or not p.path.startswith("/evento-") or not p.path.endswith(".html"):
        raise ValueError("URL outside official art-event pages")
    r=client.get(url,timeout=16,headers={"User-Agent":"CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"},allow_redirects=False)
    r.raise_for_status()
    if len(r.content)>400_000:raise ValueError("Oversize detail page")
    # Origin declares ISO-8859-1, but sends Windows-1252 punctuation and Euro.
    return BeautifulSoup(r.content.decode("cp1252",errors="replace"),"html.parser")

def parse_detail(soup):
    location=soup.select_one(".evento_ubicacion .tagselecteddark")
    venue=" ".join(location.get_text(" ",strip=True).split())[:130] if location else ""
    seccion=soup.select_one(".evento_seccion")
    lines=[]
    if seccion:
        for node in seccion.next_siblings:
            if isinstance(node,Tag) and node.name in ("div","section","table"):
                break
            if isinstance(node,NavigableString):
                for item in re.split(r"[\r\n]+",str(node)):
                    text=" ".join(item.split())
                    if text:lines.append(text)
            elif isinstance(node,Tag) and node.name not in ("script","style","iframe","br"):
                value=" ".join(node.get_text(" ",strip=True).split())
                if value:lines.append(value)
    if not lines:
        return dict(venue=venue,price="",free=None,details="",duration_min=None)
    full=" | ".join(lines)
    full=full.replace("€","€").replace("\x80","€")
    # Only structured organizer pricing claims are accepted. Do not interpret
    # "without discount" or a ticket link as a known amount.
    prices=re.findall(
        r"\b(?:PRECIO(?:\s+(?:ÚNICO|GENERAL|NORMAL|DESDE|ENTRADA))?|ENTRADA(?:\s+GENERAL)?)"
        r"\s*[:\-]\s*(\d{1,4}(?:[.,]\d{1,2})?)\s*€",full,flags=re.I)
    amounts=[]
    for p in prices:
        try:
            value=float(p.replace(",","."))
            if 0<=value<=5000:amounts.append(value)
        except ValueError:pass
    amount=min(amounts) if amounts else None
    if amount is not None:
        formatted=(str(int(amount)) if amount.is_integer() else
                   f"{amount:.2f}".replace(".",","))
        price=(f"Desde {formatted} €" if len(set(amounts))>1 else f"{formatted} €")
        free=1 if amount==0 else 0
    else:
        price="";free=None
    if re.search(r"\b(?:ENTRADA\s+GRATUITA|ACCESO\s+GRATUITO|GRATIS)\b",full,re.I):
        price="Gratis";free=1

    duration=None
    m=re.search(r"\bDURACI[ÓO]N\s*:\s*(\d{1,3})\s*(?:minutos?|min\.)",full,re.I)
    if m:
        mins=int(m.group(1))
        if 1<=mins<=600:duration=mins

    candidates=[]
    for line in lines:
        cleaned=line.replace("es un espectáculo es un espectáculo","es un espectáculo")
        if len(cleaned)<70 or len(cleaned)>900:continue
        if re.match(r"^(?:DURACI[ÓO]N|PRECIO|FESTIVAL MASDANZA|SINOPSIS|DIRECCI[ÓO]N|INT[ÉE]RPRETES|COPRODUCE|S\d{1,2}\s+OCTUBRE)",cleaned,re.I):
            continue
        if not re.search(r"[.!?](?:$|\s)",cleaned):continue
        # Use one coherent sentence, not a truncated HTML "mega text".
        sentence=re.split(r"(?<=[.!?])\s+",cleaned)[0].strip()
        if len(sentence)>=65 and len(sentence)<=300:
            candidates.append(sentence)
    summary=""
    if candidates:
        summary=candidates[0].strip()
    if duration:
        summary=(summary+" " if summary else "")+f"Duración: {duration} min."
    return dict(venue=venue,price=price,free=free,details=summary[:390],duration_min=duration)

def apply_detail(entry,detail):
    if detail.get("venue"):entry["venue"]=detail["venue"]
    if detail.get("price"):
        entry["price"]=detail["price"]
        entry["free"]=detail["free"]
    if detail.get("details"):entry["details"]=detail["details"]
    duration=detail.get("duration_min")
    if duration and len(entry.get("start",""))>=19 and not entry.get("end"):
        try:
            start=datetime.fromisoformat(entry["start"])
            entry["end"]=(start+timedelta(minutes=int(duration))).isoformat(timespec="seconds")
        except ValueError:pass
    return entry
