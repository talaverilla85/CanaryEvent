"""Conservative daily discovery of new event announcements on four town websites.

Only explicitly dated, single-day upcoming events with a named venue are
published. Ambiguous articles remain unimported; never infer a year from a
crawl date or treat a registration deadline as an event.
"""
import datetime as dt
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import venue_facts

SITES = {
 "Firgas": ("https://www.villadefirgas.es/", "villadefirgas.es"),
 "Santa María de Guía": ("https://santamariadeguia.es/", "santamariadeguia.es"),
 "Agaete": ("https://www.agaete.es/agenda", "agaete.es"),
 "Vega de San Mateo": ("https://www.vegadesanmateo.es/noticias/ferias-y-eventos", "vegadesanmateo.es"),
}
PREFIX = "Municipio · descubrimiento oficial · "
MONTHS = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
          "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
          "noviembre":11,"diciembre":12}
DATES = re.compile(r"(?<!\d)(\d{1,2})\s+de\s+("+ "|".join(MONTHS)+r")\s+de\s+(20\d{2})(?!\d)",re.I)
CLOCK = re.compile(r"\b(?:a las|a partir de las)\s+(\d{1,2})[:.]([0-5]\d)\s*(?:h|horas)?\b",re.I)
BLOCK = re.compile(r"\b(plazo|inscripci[oó]n|solicitudes|convocatoria|licitaci[oó]n|bases de|oferta de empleo|subvenciones)\b",re.I)
EVENT = re.compile(r"\b(concierto|festival|teatro|feria|mercado|taller|exposici[oó]n|fiesta|espect[aá]culo|cuentacuentos|recital|jornada cultural|presentaci[oó]n de libro)\b",re.I)

def discover(listing, host):
    links={}
    for a in listing.select("a[href]"):
        title=" ".join(a.get_text(" ",strip=True).split())
        url=urljoin("https://"+host+"/",a["href"])
        p=urlsplit(url)
        if p.scheme!="https" or p.hostname not in (host,"www."+host,host.removeprefix("www.")):continue
        if len(title)<12 or len(title)>165:continue
        if not re.search(r"/(noticia|noticias|evento|agenda|[a-z-]{12,})",p.path,re.I):continue
        if url.rstrip("/")=="https://"+host:continue
        if EVENT.search(title) and not BLOCK.search(title):links[url]=title
    return list(links.items())[:24]

def parse_article(soup,title,url,municipality,today,categorize):
    if BLOCK.search(title) or not EVENT.search(title):return None
    main=soup.select_one("article") or soup.select_one("main") or soup
    body=" ".join(main.get_text(" ",strip=True).split())[:7000]
    dates=[]
    for m in DATES.finditer(body):
        try:d=dt.date(int(m.group(3)),MONTHS[m.group(2).lower()],int(m.group(1)))
        except ValueError:continue
        if today<=d<=today+dt.timedelta(days=120):dates.append((m,d))
    unique={d for _,d in dates}
    if len(unique)!=1:return None
    match,day=dates[0]
    # The time must be next to the event date; unrelated office hours are unsafe.
    context=body[match.end():match.end()+110]
    time=CLOCK.search(context)
    start=day.isoformat()
    if time and int(time.group(1))<24:
        start+=f"T{int(time.group(1)):02d}:{int(time.group(2)):02d}:00"
    venue=venue_facts.from_description(body,municipality)
    if not venue:return None
    return {"title":title,"start":start,"end":None,"municipality":municipality,
            "venue":venue,"category":categorize(title),"free":None,"price":"",
            "details":"Actividad anunciada en la web municipal. Confirma horarios y condiciones en la publicación original.",
            "source_name":PREFIX+municipality,"source_url":url,"status":"approved"}

def fetch_and_extract(municipality,today,places,categorize,get_html):
    if municipality not in places:return []
    listing,host=SITES[municipality]
    soup=get_html(listing)
    links=discover(soup,host)
    if not links:raise ValueError("No event links found in official listing; check layout")
    events=[]
    for url,title in links:
        try:
            article=get_html(url)
            row=parse_article(article,title,url,municipality,today,categorize)
            if row:events.append(row)
        except Exception:
            # A broken article must not block all other announcements.
            continue
    return events
