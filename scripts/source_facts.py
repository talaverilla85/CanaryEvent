"""Conservative factual extraction from Cabildo's indexed event detail HTML.

No generic web crawling or copying long descriptions. Only explicit factual fields
and original outbound links are used. No ticket cost is guessed from a link.
"""
import json
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup

UNSPECIFIED={"consultar el recinto en la ficha oficial","lugar por confirmar","por determinar"}
SOCIAL_DOMAINS=("instagram.com","facebook.com","tiktok.com","youtube.com","x.com","twitter.com","wa.me","whatsapp.com")
EXTERNAL_SITES=("entradas.","tickets.","ticketmaster.","tickety.","janto.","teatros.","www." )

def display_text(s,limit=220):
    return " ".join(str(s or "").split())[:limit]

def event_schema(soup):
    """Flatten an Event from independently published JSON-LD, without assuming node order."""
    for el in soup.select('script[type="application/ld+json"]'):
        try: obj=json.loads(el.string or el.get_text())
        except (ValueError,TypeError):continue
        nodes=obj if isinstance(obj,list) else [obj]
        for node in nodes:
            if not isinstance(node,dict):continue
            possible=node.get("@graph",nodes)
            if not isinstance(possible,list):possible=[possible]
            for item in possible:
                if not isinstance(item,dict):continue
                types=item.get("@type",[])
                if isinstance(types,str):types=[types]
                if any(t=="Event" or t.endswith("/Event") for t in types):return item
    return {}

def money(value):
    if value is None or isinstance(value,bool):return None
    try:
        if isinstance(value,str):
            value=value.replace(" ","").replace(",",".")
        n=float(value)
    except (TypeError,ValueError):return None
    if not (0<=n<=5000):return None
    return n

def display_money(amount):
    return (f"{int(amount)}" if amount.is_integer() else f"{amount:.2f}".replace(".",","))+" €"

def parse_price(soup, schema, single_session):
    """One verified event-wide ticket amount or explicit free-entry statement."""
    if schema.get("isAccessibleForFree") is True:return "Gratis",1
    offers=schema.get("offers")
    offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
    prices=[]
    for offer in offers:
        if not isinstance(offer,dict):continue
        cur=str(offer.get("priceCurrency","EUR")).upper()
        amount=money(offer.get("price"))
        if cur in ("EUR","€") and amount is not None:
            prices.append(amount)
    if prices:
        amounts=sorted(set(prices))
        if len(amounts)==1:
            return ("Gratis",1) if amounts[0]==0 else (display_money(amounts[0]),0)
        return "Desde "+display_money(amounts[0]), 0
    # Multiple activities under a single programme must NOT receive a made-up shared tariff.
    if not single_session:return "",None
    for el in soup.select('[itemprop="price"],.event-detail__price,.event-detail__ticket-price'):
        amt=money(el.get("content") or el.get_text(" ",strip=True).replace("€",""))
        if amt is not None:return ("Gratis",1) if amt==0 else (display_money(amt),0)
    # Only explicit *event-wide* pricing with a named label and currency.
    desc=display_text(schema.get("description"),3000)
    if re.search(r"\b(?:entrada\s+gratuita|acceso\s+gratuito|entrada\s+libre|gratis)\b",desc,re.I):
        return "Gratis",1
    matches=re.findall(
        r"\b(?:precio\s+(?:único|general|normal)|entrada\s+general)\s*:\s*"
        r"(\d{1,4}(?:[,.]\d{1,2})?)\s*(?:€|euros?)",desc,re.I)
    if len(matches)==1:
        amt=money(matches[0])
        if amt is not None:return ("Gratis",1) if amt==0 else (display_money(amt),0)
    return "",None

def verified_venue(soup,schema,municipality,norm):
    texts=[display_text(el.get_text(" ",strip=True),180) for el in soup.select(".event-detail__details-list p.event-detail__text")]
    for idx,text in enumerate(texts):
        if norm(text)==norm(municipality) and idx>0:
            prev=texts[idx-1]
            if (not re.fullmatch(r"\d{2}/\d{2}/20\d{2}.*",prev) and
                prev.lower() not in UNSPECIFIED and len(prev)>3):
                return prev
    place=schema.get("location")
    if isinstance(place,list):place=place[0] if place else None
    if isinstance(place,dict):
        name=display_text(place.get("name"),130)
        if name and norm(name)!=norm(municipality) and name.lower() not in UNSPECIFIED:
            return name
    # A named location in a description isn't reliable when an event lists multiple venues.
    return ""

def valid_outbound(url):
    if not isinstance(url,str):return ""
    try:
        p=urlsplit(url.strip())
        if p.scheme!="https" or not p.hostname or p.username or p.password or len(url)>600:return ""
        host=p.hostname.lower().strip(".")
        if host in ("www.eventosgrancanaria.com","eventosgrancanaria.com"):return ""
        if host=="localhost" or host.endswith(".local") or host.endswith(".internal"):return ""
        if host in ("www.google.com","google.com","maps.google.com"):
            return ""  # map directions are not organizer pages
        if any(x in host for x in ("127.0.0.","169.254.","192.168.","10.0.","0.0.0.","[::","::1")):return ""
        # Outgoing links published by the Cabildo are displayed as references,
        # never crawled or promoted as guaranteed ticket sellers.
        return url.strip()
    except ValueError:return ""

def organizer_link(soup):
    # In the official detail card, the outward-facing reference is part of the metadata.
    for el in soup.select(".event-detail__details-list a[href]"):
        href=valid_outbound(el.get("href"))
        if href:
            host=(urlsplit(href).hostname or "").lower()
            if not any(host==s or host.endswith("."+s) for s in SOCIAL_DOMAINS):
                return href
    return ""

def factual_summary(schema,venue,municipality,multi_day):
    """Authored from facts instead of copying the organizer's protected synopsis."""
    if multi_day:
        return "Periodo de actividad con varias fechas. Consulta sesiones, horarios y condiciones en la fuente original."
    if venue:
        return "Actividad en "+venue+", "+municipality+". Consulta los detalles y posibles cambios con la organización."
    return "Actividad en "+municipality+". Consulta el recinto, el programa y las condiciones con el organizador."

def enhance(soup,municipality,norm,multi_day):
    schema=event_schema(soup)
    venue=verified_venue(soup,schema,municipality,norm)
    price,free=parse_price(soup,schema,not multi_day)
    external=organizer_link(soup)
    return {
      "venue":venue,
      "price":price,
      "free":free,
      "details":factual_summary(schema,venue,municipality,multi_day),
      "organizer_url":external,
    }
