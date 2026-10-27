"""A tiny registry of explicitly reviewed official event/venue corroborations.

This is deliberately NOT general NER: every match needs exact event title,
Cabildo event URL, exact town, an official article with named location and
date/year evidence, and robots permission. Failed fetches never add a place.
"""
from __future__ import annotations
import re
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

SOURCE="Recintos · confirmaciones de noticias oficiales"
USER_AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
FACTS=(
 {"title":"Oliva Lara. Último pintor indigenista americano",
  "municipality":"Gáldar","venue":"Museo Agáldar de Historia de la Ciudad",
  "url":"https://www.galdar.es/el-museo-agaldar-presenta-una-exposicion-dedicada-a-la-obra-del-pintor-indigenista-oliva-lara/",
  "tokens":("oliva lara","museo agáldar de historia de la ciudad","15 de noviembre de 2026","9 de octubre"),
  "source_prefix":"https://www.eventosgrancanaria.com/event/"},
 {"title":"Frontón King 2026",
  "municipality":"Gáldar","venue":"Ola de El Frontón",
  "url":"https://www.galdar.es/el-gran-canaria-fronton-king-2026-vuelve-a-situar-a-galdar-en-el-centro-mundial-del-bodyboard/",
  "tokens":("frontón king","ola de el frontón","17 al 31 de octubre","2026"),
  "source_prefix":"https://www.eventosgrancanaria.com/event/"},
 {"title":"ExpoDeca 2026, Feria de la Actividad Física y el Deporte de Canarias",
  "municipality":"Las Palmas de Gran Canaria","venue":"Plaza de la Música (Plaza Jerónimo Saavedra)",
  "url":"https://infecar.es/ferias-y-eventos/expodeca-2026-feria-de-la-actividad-fisica-y-el-deporte-de-canarias/",
  "tokens":("expodeca","plaza jerónimo saavedra","plaza de la música","12 al 15 de noviembre"),
  "source_prefix":"https://www.eventosgrancanaria.com/event/"},
)

def normalized(value):
    import unicodedata
    s=unicodedata.normalize("NFKD",str(value).casefold())
    return " ".join("".join(ch for ch in s if not unicodedata.combining(ch)).split())

def fetch_official(session,url):
    from urllib.parse import urlsplit
    parts=urlsplit(url)
    if parts.scheme!="https" or parts.hostname not in ("www.galdar.es","infecar.es"):
        raise ValueError("Not an allowlisted municipality/organizer")
    host=f"https://{parts.hostname}"
    headers={"User-Agent":USER_AGENT}
    rp=session.get(host+"/robots.txt",timeout=12,headers=headers,allow_redirects=False)
    if rp.status_code==200:
        policy=RobotFileParser()
        policy.parse(rp.text.splitlines())
        if not policy.can_fetch(USER_AGENT,url):
            raise PermissionError("robots disallows official article")
    elif rp.status_code not in (404,410):
        raise RuntimeError("Official robots unavailable")
    response=session.get(url,timeout=18,headers=headers,allow_redirects=False)
    if response.status_code!=200 or len(response.content)>2_000_000:
        raise ValueError("Official article unavailable")
    soup=BeautifulSoup(response.content,"html.parser")
    container=soup.select_one("article") or soup.select_one("main")
    return normalized((container or soup).get_text(" ",strip=True))

def enrich(conn,now,today,*,session=None):
    session=session or requests.Session()
    rows=[dict(x) for x in conn.execute(
        """SELECT id,title,municipality,venue,source_url,start FROM events
         WHERE status='approved' AND substr(COALESCE("end",start),1,10)>=?""",
        (today.isoformat(),))]
    checked=updated=0
    errors=[]
    for spec in FACTS:
        targeted=[e for e in rows
                  if e["municipality"]==spec["municipality"]
                  and normalized(e["title"])==normalized(spec["title"])
                  and e["source_url"].startswith(spec["source_prefix"])
                  and e["venue"].lower().startswith("consultar el recinto")]
        if not targeted:continue
        checked+=1
        try:
            body=fetch_official(session,spec["url"])
            if not all(normalized(tok) in body for tok in spec["tokens"]):
                raise ValueError("Official article does not corroborate all facts")
            for item in targeted:
                conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                             (spec["venue"],now,item["id"]))
                updated+=1
        except (ValueError,PermissionError,RuntimeError,requests.RequestException) as exc:
            errors.append({"url":spec["url"],"error_type":type(exc).__name__})
    return {"source":SOURCE,"checked":checked,"updated":updated,"errors":errors}
