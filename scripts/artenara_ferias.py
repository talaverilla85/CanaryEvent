"""Two 2026 autumn fair dates verified from the Ayuntamiento de Artenara.

Only the 9 Oct 2026 municipal archive's documented fair announcements
are imported; a yearly recurring date is not assumed for future years.
"""
import datetime as dt
import requests
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup

NAME="Ayuntamiento de Artenara · ferias tradicionales 2026"
ROOT="https://www.artenara.es"
CATEGORY=ROOT+"/portal-ciudadano/category/eventos/"
ARCHIVE=ROOT+"/portal-ciudadano/2026/10/09/"
UA="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":UA}
ITEMS=(
 {"url":ROOT+"/portal-ciudadano/noticias/vi-feria-de-las-tradiciones-en-artenara/",
  "title":"VI Feria de las Tradiciones · Artenara","date":"2026-11-01",
  "tokens":("1 de noviembre","artesanía","tradiciones"),
  "details":"Feria de las tradiciones con productos locales, música y talleres. Consulta el programa en el Ayuntamiento."},
 {"url":ROOT+"/portal-ciudadano/noticias/ii-edicion-del-mercadillo-tradicional-de-artenara-%f0%9f%8d%82/",
  "title":"II Mercadillo Tradicional · Artenara","date":"2026-10-31",
  "tokens":("31 de octubre","artesanos","pintacaras"),
  "details":"Mercadillo con artesanía, música y actividades familiares. Consulta horarios y condiciones en el Ayuntamiento."}
)
def fetch(client=requests):
    robots=client.get(ROOT+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if robots.status_code==200:
        p=RobotFileParser();p.parse(robots.text.splitlines())
        if any(not p.can_fetch(UA,u) for u in [CATEGORY,ARCHIVE]+[r["url"] for r in ITEMS]):
            raise PermissionError("Artenara disallows a required official page")
    elif robots.status_code not in (404,410):
        raise RuntimeError(f"Artenara robots unavailable: {robots.status_code}")
    pages={}
    for url in [CATEGORY,ARCHIVE]+[r["url"] for r in ITEMS]:
        resp=client.get(url,headers=HEADERS,timeout=22,allow_redirects=False)
        if resp.status_code!=200:raise RuntimeError(f"Artenara page HTTP {resp.status_code}: {url}")
        if len(resp.content)>1_500_000:raise ValueError("Artenara page too large")
        pages[url]=BeautifulSoup(resp.content,"html.parser")
    return pages
def extract(pages,today,places,categorize):
    if "Artenara" not in places or today>dt.date(2026,11,1):return []
    archived=pages[ARCHIVE]
    if "9 de octubre de 2026" not in archived.get_text(" ",strip=True).lower():
        raise ValueError("Artenara news archive missing 2026 publication date")
    linked={a.get("href","").rstrip("/").lower() for a in archived.select('a[href]')}
    events=[]
    for item in ITEMS:
        if item["date"]<today.isoformat():continue
        link=item["url"].rstrip("/").lower()
        if link not in linked:raise ValueError(f"Artenara announcement not found in 2026 archive: {link}")
        category_link={a.get("href","").rstrip("/").lower() for a in pages[CATEGORY].select("article a[href]")}
        if link not in category_link:raise ValueError(f"Artenara news not in official Events category: {link}")
        page=pages[item["url"]]
        section=page.select_one(".elementor-widget-theme-post-content")
        if section is None:raise ValueError("Artenara article body unavailable")
        words=section.get_text(" ",strip=True).casefold()
        if not all(t.casefold() in words for t in item["tokens"]):
            raise ValueError(f"Artenara announcement no longer verifies {item['title']}")
        # Two independent event-matched references confirm 1 Nov 2026
        # VI Feria de Tradiciones at Plaza de San Mat?as. This is NOT a
        # blanket fallback for all Artenara markets/festivals.
        verified_venue=("Plaza de San Mat?as" if item["date"]=="2026-11-01"
                        and "Tradiciones" in item["title"] else
                        "Consultar el recinto en la ficha oficial")
        events.append({
          "title":item["title"],"start":item["date"],"end":None,"municipality":"Artenara",
          "venue":verified_venue,
          "category":categorize(item["title"]),"free":None,"price":"",
          "details":item["details"],"source_name":NAME,"source_url":item["url"],
          "status":"approved"
        })
    return events
