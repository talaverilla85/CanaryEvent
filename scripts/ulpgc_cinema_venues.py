"""Official university film-cycle venue corroboration from an independent ULPGC page.

The ULPGC agenda endpoints can return HTTP 403. The University's public
library article (same first-party organisation) names the film programme,
its specific 2026 window, 19:00, and its hall. Join ONLY exact known
Cabildo film title/date pairs; do not generalize to every ULPGC event.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import venue_quality

NAME="ULPGC · cine documental con recinto confirmado"
ARTICLE="https://biblioteca.ulpgc.es/blogs/theend/2026/10/cine-en-la-ulpgc-para-el-segundo-semestre-del-ano"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":AGENT,"Accept":"text/html"}
HALL="Salón de Actos del Edificio de Humanidades"
DATES={
  "2026-10-30":"el angel azul",
  "2026-11-06":"asesinato",
  "2026-11-13":"m el vampiro de dusseldorf",
  "2026-11-20":"viva la libertad",
  "2026-11-27":"scarface el terror del hampa",
  "2026-12-04":"amame esta noche",
  "2026-12-11":"una mujer fuera de la ley",
  "2026-12-18":"la mujer de todos",
}
SOURCE="https://www.eventosgrancanaria.com/event/"
ORGANIZER="https://www.ulpgc.es/agenda/2026/"
PREFIX="aula de cine ciclo los modernos anos 30 "

def norm(t):
    s=unicodedata.normalize("NFKD",str(t or "").casefold())
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+",s))

def verified_article_text(html):
    soup=BeautifulSoup(html,"html.parser")
    root=soup.select_one("article") or soup.select_one("main")
    if root is None:return ""
    text=norm(root.get_text(" ",strip=True))
    # Direct proof of THIS cycle and this exact venue, not a university footer.
    required=(
       "cine en la ulpgc para el segundo semestre del ano",
       "del 23 de octubre al 18 de diciembre",
       "los modernos",
       "el angel azul",
       "asesinato",
       "vampiro de dusserldorf", # original university spelling
       "viva la libertad",
       "scarface el terror del hampa",
       "amame este noche",      # original university spelling
       "una mujer fuera de la ley",
       "la mujer de todos",
       "las proyecciones tendran lugar a las 19 00 en el salon de actos del edificio de humanidades",
    )
    return text if all(x in text for x in required) else ""

def event_qualifies(e):
    if e.get("municipality")!="Las Palmas de Gran Canaria":
        return False
    if not str(e.get("source_url") or "").startswith(SOURCE):
        return False
    if not str(e.get("organizer_url") or "").startswith(ORGANIZER):
        return False
    day=str(e.get("start") or "")[:10]
    suffix=DATES.get(day)
    if not suffix:return False
    if norm(e.get("title"))!=PREFIX+suffix:
        return False
    start=str(e.get("start") or "")
    if len(start)>10 and (len(start)<16 or start[11:16]!="19:00"):
        return False
    return not venue_quality.named_venue(e)

def download_article(client):
    r=client.get("https://biblioteca.ulpgc.es/robots.txt",
                 headers=HEADERS,timeout=12,allow_redirects=False)
    if r.status_code not in (200,404,410):
        raise RuntimeError("ULPGC library robots status unavailable")
    policy=RobotFileParser()
    if r.status_code==200:policy.parse(r.text.splitlines())
    else:policy.allow_all=True
    if not policy.can_fetch(AGENT,ARTICLE):
        raise PermissionError("ULPGC library disallows retrieval")
    res=client.get(ARTICLE,headers=HEADERS,timeout=18,allow_redirects=False)
    if res.status_code!=200 or len(res.content)>1_300_000:
        raise RuntimeError("ULPGC article unavailable")
    if "html" not in res.headers.get("content-type","text/html"):
        raise ValueError("ULPGC article unexpectedly not HTML")
    return verified_article_text(res.content)

def enrich(conn,now,today,*,session=None):
    report={"source":NAME,"checked_at":now,"found":0,"added":0,
            "changed":0,"eligible":0,"error":""}
    events=[dict(row) for row in conn.execute(
        """SELECT id,title,start,municipality,venue,source_url,organizer_url
           FROM events WHERE status='approved' AND
           substr(COALESCE("end",start),1,10)>=?""",
        (today.isoformat(),))]
    targets=[e for e in events if event_qualifies(e)]
    report["eligible"]=len(targets)
    if not targets:return report
    try:
        proof=download_article(session or requests.Session())
        report["found"]=1
        if not proof:raise ValueError("Official article does not corroborate 2026 programme")
        for event in targets:
            conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                         (HALL,now,event["id"]))
            report["changed"]+=1
    except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
        report["error"]=type(exc).__name__
    conn.commit()
    return report
