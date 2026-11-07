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


# Santa María de Guía's home page uses X-Theme recent-post cards, not an
# event-feed. Only article headings are candidate titles; card excerpts
# contain unrelated metadata, publication dates and summaries.
GUIA_HOST="santamariadeguia.es"
GUIA_EVENTS=re.compile(
 r"\b(?:finaos|correr|carrera|concierto|festival|circo|circus|teatro|"
 r"feria|mercado|espect[aá]culo|taller(?:es)?|fiesta|recital|"
 r"patearte|senderismo|ruta(?:s)?|cuentacuentos)\b",re.I)
GUIA_MENTION=re.compile(
 r"(?<!\d)([0-3]?\d)\s+de\s+("+"|".join(MONTHS)+
 r")(?:\s+de\s+(20\d{2}))?(?!\d)",re.I)
GUIA_RANGE=re.compile(
 r"\b(?:del|desde\s+el)\s+[0-3]?\d\s+(?:al|hasta\s+el)\s+[0-3]?\d"
 r"\s+de\s+(?:"+"|".join(MONTHS)+r")\b",re.I)
GUIA_PRIMARY_TIME=re.compile(
 r"\b(?:tendr[áa]\s+lugar|dar[áa]\s+comienzo|se\s+celebrar[áa]|"
 r"se\s+celebra|comenzar[áa]|comienza|se\s+iniciar[áa]|arrancar[áa])"
 r"\b.{0,145}?\ba\s+las\s+([01]?\d|2[0-3]):([0-5]\d)\b",re.I)

def discover_guia(listing):
    """Read verified article *headings* from Guía's official home page."""
    links={}
    for card in listing.select(".x-recent-posts a[href]"):
        heading=card.select_one("h3.h-recent-posts")
        if not heading:continue
        title=" ".join(heading.get_text(" ",strip=True).split())
        url=urljoin("https://"+GUIA_HOST+"/",card.get("href",""))
        parts=urlsplit(url)
        if (parts.scheme!="https" or parts.hostname!=GUIA_HOST
            or parts.query or parts.fragment
            or not re.fullmatch(r"/[a-z0-9][a-z0-9-]{14,}/",parts.path)
            or not 12<=len(title)<=165
            or not GUIA_EVENTS.search(title)
            or BLOCK.search(title)):
            continue
        links[url]=title
    return list(links.items())[:24]


def parse_guia_article(soup,title,url,today,categorize):
    """Only one explicitly dated activity with verifiable primary time and place.

    Publication *year*, not crawler date, disambiguates bare '21 de noviembre'.
    An article with several dates, a multi-day range or an unverified hall is
    intentionally held back, not published with invented event metadata.
    """
    if not GUIA_EVENTS.search(title) or BLOCK.search(title):return None
    article=soup.select_one("article")
    pub=article.select_one("time[datetime]") if article else None
    body_el=article.select_one(".entry-content") if article else None
    if not(pub and body_el):return None
    try:published=dt.date.fromisoformat(pub["datetime"][:10])
    except (ValueError,KeyError):return None
    body=" ".join(body_el.get_text(" ",strip=True).split())[:7000]
    if GUIA_RANGE.search(body):return None
    days=set()
    for match in GUIA_MENTION.finditer(body):
        month=MONTHS[match.group(2).lower()]
        year=int(match.group(3)) if match.group(3) else published.year
        try:day=dt.date(year,month,int(match.group(1)))
        except ValueError:continue
        if (published-dt.timedelta(days=3)<=day<=published+dt.timedelta(days=120)
            and today<=day<=today+dt.timedelta(days=120)):
            days.add(day)
    if len(days)!=1:return None
    # A calendar date and the primary performance hour must be established.
    primary=GUIA_PRIMARY_TIME.findall(body)
    times={(int(h),int(m)) for h,m in primary}
    if len(times)!=1:return None
    hour,minute=next(iter(times))
    venue=""
    # Venue identities below are quoted directly in the municipality's own
    # story and tied to the event action, never inferred from mentions of town.
    if re.search(
        r"\bse\s+celebrar[áa]\s+en\s+la\s+Iglesia\s+de\s+Santa\s+Mar[ií]a\s+de\s+Gu[ií]a\b",
        body,re.I):
        venue="Iglesia de Santa María de Guía"
    elif re.search(
        r"\bplaza\s+de\s+San\s+Pedro\s+de\s+La\s+Atalaya\b"
        r".{0,85}\b(?:punto\s+de\s+encuentro|salida)\b",body,re.I):
        venue="Plaza de San Pedro de La Atalaya"
    else:
        # Generic recognizer must find a unique concrete place; otherwise
        # the story stays out of the public catalog.
        venue=venue_facts.from_description(body[:1000],"Santa María de Guía")
    if not venue:return None
    return {"title":title,"start":next(iter(days)).isoformat()+
            f"T{hour:02d}:{minute:02d}:00","end":None,
            "municipality":"Santa María de Guía","venue":venue,
            "category":categorize(title),"free":None,"price":"",
            "details":"Actividad confirmada en una noticia del Ayuntamiento de Guía.",
            "source_name":PREFIX+"Santa María de Guía","source_url":url,
            "status":"approved"}

def discover(listing, host):
    if host==GUIA_HOST:return discover_guia(listing)
    links={}
    for a in listing.select("a[href]"):
        title=" ".join(a.get_text(" ",strip=True).split())
        if title.casefold() in ("leer más", "read more", "más información", "ver más"):
            for ancestor in list(a.parents)[:4]:
                heading=ancestor.find(["h2","h3","h4","h5"])
                if heading:
                    candidate=" ".join(heading.get_text(" ",strip=True).split())
                    if candidate and candidate.casefold()!=title.casefold():
                        title=candidate
                        break
        url=urljoin("https://"+host+"/",a["href"])
        p=urlsplit(url)
        if p.scheme!="https" or p.hostname not in (host,"www."+host,host.removeprefix("www.")):continue
        if len(title)<12 or len(title)>165:continue
        if not re.search(r"/(noticia|noticias|evento|agenda|[a-z-]{12,})",p.path,re.I):continue
        if url.rstrip("/")=="https://"+host:continue
        if EVENT.search(title) and not BLOCK.search(title):links[url]=title
    return list(links.items())[:24]

def parse_article(soup,title,url,municipality,today,categorize):
    if municipality=="Santa María de Guía":
        return parse_guia_article(soup,title,url,today,categorize)
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
