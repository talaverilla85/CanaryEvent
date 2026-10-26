"""Individually verified activities from Ingenio's autumn 2026 poster.

Only rows with a verifiable activity venue are publishable. The poster is
an official Cabildo event whose organiser is Ingenio's youth department;
the actual location may be another municipality.
"""
from __future__ import annotations
import datetime as dt
from bs4 import BeautifulSoup

NAME="Juventud de Ingenio · programa de otoño desglosado"
PROGRAM_URL=("https://www.eventosgrancanaria.com/event/E-20260924-0017/"
             "programacion-otono-2026-juventud-de-ingenio")
OFFICIAL_IMAGE_ID="6aaf8ba0013a6268e079d56c"
PUBLISH_THROUGH=dt.date(2026,11,17)

# Manually verified from the official programme image, 2026-10-26.
# The 6 November roller-hockey item only says "en Ingenio": venue
# is NOT specific, so it is retained in the review queue, not published.
UNRESOLVED=(
 {"title":"Hockey patín en Ingenio", "date":"2026-11-06",
  "time":"17:30 a 19:30 aprox.", "municipality":"Ingenio",
  "reason":"El cartel no identifica la instalación deportiva o punto de encuentro"},
)

ACTIVITIES=(
 {
  "title":"Iniciación al boxeo · Juventud de Ingenio",
  "start":"2026-11-17T19:00:00",
  "end":"2026-11-17T20:30:00",
  "municipality":"Las Palmas de Gran Canaria",
  "venue":"Barranco de la Ballena (zona de actividad; acceso exacto por confirmar)",
  "category":"deporte",
  "details":("Actividad para jóvenes de 12 a 30 años, organizada por Juventud "
    "de Ingenio. La sede anunciada es el Barranco de la Ballena, en Las Palmas "
    "de Gran Canaria. Confirma el punto de encuentro e inscripción con la organización."),
 },
)

def source_is_unchanged(html):
 soup=BeautifulSoup(html,"html.parser")
 h1=soup.select_one("h1.event-detail__title")
 if h1 is None or "programacion otono 2026 - juventud de ingenio" not in (
   "".join(c for c in __import__('unicodedata').normalize("NFKD",h1.get_text(" ",strip=True).lower())
           if not __import__('unicodedata').combining(c))
 ):
  raise ValueError("El título del programa oficial de Ingenio ha cambiado")
 texts=" ".join(el.get_text(" ",strip=True) for el in
    soup.select(".event-detail__details-list p.event-detail__text"))
 if "24/09/2026 - 17/11/2026" not in texts:
  raise ValueError("Las fechas del programa oficial ya no coinciden")
 found=False
 for im in soup.select("img[src]"):
  if OFFICIAL_IMAGE_ID in str(im.get("src","")):found=True;break
 if not found:raise ValueError("El cartel oficial fue reemplazado; revisar actividades antes de publicar")
 return True

def extract(html,today,places):
 if today>PUBLISH_THROUGH:return []
 source_is_unchanged(html)
 events=[]
 for e in ACTIVITIES:
  if e["start"][:10]<today.isoformat():continue
  if e["municipality"] not in places:continue
  events.append({**e,"free":None,"price":"",
   "source_name":NAME,"source_url":PROGRAM_URL,"status":"approved"})
 return events
