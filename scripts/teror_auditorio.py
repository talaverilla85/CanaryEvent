"""Auditorio de Teror season program, from published municipal narrative.

Only dated, individually identified acts are imported. Generic annual event
lists without a year must never be converted into fictitious future events.
"""
import datetime as dt,re,html
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests

NAME="Ayuntamiento de Teror · programación del Auditorio"
URL="https://teror.es/el-auditorio-de-teror-presenta-la-programacion-para-el-proximo-cuatrimestre/"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT}
MONTHS={"OCTUBRE":10,"NOVIEMBRE":11,"DICIEMBRE":12,"ENERO":1}
BLOCK=re.compile(r"(?m)^\s*(\d{1,2})\.\-\s*(.+?)\s*$")
SINGLE=re.compile(r"(?im)\b(\d{1,2})\s+(?:DE\s+)?(OCTUBRE|NOVIEMBRE|DICIEMBRE|ENERO)\s+DE\s+(202[67])\b")
PERIOD=re.compile(r"(?im)\bDEL\s+(\d{1,2})\s+AL\s+(\d{1,2})\s+DE\s+(OCTUBRE|NOVIEMBRE|DICIEMBRE|ENERO)\s+DE\s+(202[67])\b")
TIME=re.compile(r"(?im)^\s*(\d{1,2}):(\d{2})\s+HORAS?\b")
PRICE=re.compile(r"(?im)^\s*PRECIO\s*:?\s*(\d{1,3}(?:[,.]\d{1,2})?)\s*€")
def get_html(client=requests):
    r=client.get("https://teror.es/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if r.status_code!=200:raise RuntimeError(f"Teror robots HTTP {r.status_code}")
    p=RobotFileParser();p.parse(r.text.splitlines())
    if not p.can_fetch(AGENT,URL):raise PermissionError("Teror disallows program")
    r=client.get(URL,headers=HEADERS,timeout=22,allow_redirects=False)
    if r.status_code!=200:raise RuntimeError(f"Teror program HTTP {r.status_code}")
    if len(r.content)>1_500_000:raise ValueError("Teror program too large")
    return BeautifulSoup(r.content,"html.parser")
def extract(soup,today,places,categorize):
    if "Teror" not in places:return []
    article=soup.select_one("article .entry-content") or soup.select_one("article")
    if not article:raise ValueError("Teror missing program article")
    txt=article.get_text("\n",strip=True)
    if "PROGRAMA:" not in txt:raise ValueError("Teror article no longer contains the printed program")
    txt=txt.split("PROGRAMA:",1)[1]
    matches=list(BLOCK.finditer(txt))
    if len(matches)<9:raise ValueError("Teror program expected many individually numbered acts")
    events=[]
    for i,m in enumerate(matches):
        section=txt[m.end():matches[i+1].start() if i+1<len(matches) else len(txt)]
        title=html.unescape(m.group(2).strip(" ."))[:170]
        period=PERIOD.search(section[:400])
        date=SINGLE.search(section[:400])
        if period:
            start=dt.date(int(period.group(4)),MONTHS[period.group(3).upper()],int(period.group(1)))
            end=dt.date(int(period.group(4)),MONTHS[period.group(3).upper()],int(period.group(2)))
            if end<start:continue
            start_value=start.isoformat();end_value=end.isoformat()
        elif date:
            start=dt.date(int(date.group(3)),MONTHS[date.group(2).upper()],int(date.group(1)))
            end=start;end_value=None
            tm=TIME.search(section[:500])
            if tm:
                hour,minute=int(tm.group(1)),int(tm.group(2))
                if hour>23 or minute>59:continue
                start_value=f"{start.isoformat()}T{hour:02d}:{minute:02d}:00"
            else:start_value=start.isoformat()
        else:continue
        if end<today or start>today+dt.timedelta(days=180):continue
        price_match=PRICE.search(section[:700])
        price=""
        if price_match and "fianza" not in section[:700].lower():
            price=price_match.group(1).replace(".",",")+" €"
        events.append(dict(title=title,start=start_value,end=end_value,
               municipality="Teror",venue="Auditorio de Teror",
               category=categorize(title),free=None,price=price,
               details="Espectáculo de la temporada cultural del Auditorio de Teror. Consulta las condiciones de entrada y el horario en el programa municipal.",
               source_name=NAME,source_url=URL,status="approved"))
    if not events and today<=dt.date(2027,1,31):
        raise ValueError("Teror official article has no verifiable future individual shows")
    return events
