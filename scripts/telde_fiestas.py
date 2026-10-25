"""Verified 2026 Telde municipal festivities from named original notices.

These notices concern 2026 only; events expire and cannot silently be
repeated in future years. No invented attendance or admission prices.
"""
import datetime as dt
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

NAME="Ayuntamiento de Telde · fiestas y cultura 2026"
BASE="https://www.telde.es"
NOTICES={
"finaos": BASE+"/telde-celebrara-los-finaos-el-31-de-octubre-con-tradicion-cuentos-y-conciertos-en-la-plaza-de-san-juan/",
"gregorio":BASE+"/areas/ocio-cultura-y-juventud/festejos-y-ferias/fiestas-de-san-gregorio/",
"feria":BASE+"/telde-abre-el-plazo-para-participar-en-la-feria-de-artesania-de-las-fiestas-de-san-gregorio-taumaturgo/",
}
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT}
# Each entry's tokens must appear verbatim (case-insensitive) in its assigned
# municipal notice. This blocks stale/hijacked pages from generating events.
ITEMS=(
 ("finaos","El legado de los Finaos · Telde","2026-10-31T19:30:00",None,
  "Casa Condal, Telde",("31 de octubre","19.30 horas","legado de los Finaos")),
 ("finaos","Cuentos de Finaos · Telde","2026-10-31T20:00:00",None,
  "Iglesia Hospitalaria de San Pedro Mártir de Verona",("31 de octubre","20.00 horas","Taller de Juglares")),
 ("finaos","El Último Que Cierre · Finaos Telde","2026-10-31T20:30:00",None,
  "Plaza de San Juan, Telde",("31 de octubre","20.30 horas","El Último Que Cierre")),
 ("finaos","Arístides Moreno y 101 Brass Band · Finaos Telde","2026-10-31T22:30:00",None,
  "Plaza de San Juan, Telde",("31 de octubre","22.30 horas","Arístides Moreno")),
 ("gregorio","Pasacalles anunciador de San Gregorio · Telde","2026-11-06T19:00:00",None,
  "Plaza de San Gregorio, Telde",("6 de noviembre","19.00 horas","pasacalles")),
 ("gregorio","Pregón de las fiestas de San Gregorio · Telde","2026-11-06T20:00:00",None,
  "Plaza de San Gregorio, Telde",("6 de noviembre","20.00 horas","Maricarmen Hernández")),
 ("feria","Feria de Artesanía de San Gregorio · Telde","2026-11-15","2026-11-17",
  "Entorno de la plaza de San Gregorio, Telde",("15, 16 y 17 de noviembre de 2026","10.00 a 21.00","09.00 a 14.00")),
)
def read_official(client=requests):
    rp=client.get(BASE+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if rp.status_code!=200:raise RuntimeError(f"Telde robots HTTP {rp.status_code}")
    checker=RobotFileParser();checker.parse(rp.text.splitlines())
    if any(not checker.can_fetch(AGENT,url) for url in NOTICES.values()):
        raise PermissionError("Telde notice disallowed by robots")
    pages={}
    for key,url in NOTICES.items():
        response=client.get(url,headers=HEADERS,timeout=22,allow_redirects=False)
        if response.status_code!=200:raise RuntimeError(f"Telde {key} HTTP {response.status_code}")
        if len(response.content)>1_500_000:raise ValueError("Telde notice unusually large")
        pages[key]=BeautifulSoup(response.content,"html.parser")
    return pages
def extract(pages,today,places,categorize):
    if "Telde" not in places:return []
    if today>dt.date(2026,11,17):return []
    extracts={}
    for key in NOTICES:
        node=pages[key].select_one("article") if key in pages else None
        if node is None:raise ValueError(f"Telde municipal notice missing article {key}")
        extracts[key]=node.get_text(" ",strip=True).casefold()
        if "2026" not in extracts[key]:raise ValueError("Telde notice did not verify the 2026 program")
    events=[]
    for key,title,start,end,venue,tokens in ITEMS:
        until=(end or start)[:10]
        if until<today.isoformat():continue
        if not all(token.casefold() in extracts[key] for token in tokens):
            raise ValueError(f"Telde announcement no longer verifies {title}")
        events.append(dict(title=title,start=start,end=end,municipality="Telde",
            venue=venue,category=categorize(title),free=None,price="",
            details="Actividad anunciada por el Ayuntamiento de Telde. Consulta el programa municipal para posibles cambios de horario y condiciones de acceso.",
            source_name=NAME,source_url=NOTICES[key],status="approved"))
    return events
