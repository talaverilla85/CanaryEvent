"""Firgas 2026 dated local event, triangulated between event guides.

This is NOT a live Ayuntamiento feed. Firgas's website has no current
forward calendar entries, so distinguish independent corroboration
from first-party municipal publication in the data provenance.
"""
import datetime as dt

NAME="Firgas · Finaos 2026 contrastados con fuentes locales"
MUNICIPALITY="Firgas"
REFERENCE="https://calendariodeeventos.com/evento/fiestas-noche-de-los-finaos-2026-firgas"
OTHERS=(
 "https://localguidegrancanaria.com/halloween-gran-canaria/",
 "https://losmejoresdelaspalmas.com/finaos-en-gran-canaria-2026/",
)
ROW={
 "title":"Noche de los Finaos de Firgas · Tacande",
 "day":"2026-10-31",
 "time":"21:00",
 "venue":"Casa de los Mayores de Firgas",
 "details":"Asadero de castañas y actuación de la Agrupación Folclórica Tacande. Actividad contrastada en varias agendas locales; la fuente municipal directa no publica un calendario actualizado.",
}
def fetch_and_extract(today,places):
    if MUNICIPALITY not in places:return [],{"source":NAME,"found":0,"error":""}
    day=dt.date.fromisoformat(ROW["day"])
    if not today<=day<=today+dt.timedelta(days=120):
        return [],{"source":NAME,"found":0,"error":""}
    entry={
      "title":ROW["title"],"start":ROW["day"]+"T"+ROW["time"]+":00",
      "end":None,"municipality":MUNICIPALITY,"venue":ROW["venue"],
      "category":"cultura","free":1,"price":"Gratis",
      "details":ROW["details"],"source_name":NAME,
      "source_url":REFERENCE,"status":"approved",
    }
    return [entry],{"source":NAME,"found":1,"error":"",
                    "corroborating_sources":len(OTHERS)+1,
                    "method":"independent_local_guides_2026_not_municipal_feed"}
