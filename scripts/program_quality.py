"""Quality gate: a programme poster is a source, not an individual plan.

Works at export time, so a daily official-source sync cannot accidentally
republish historic generic brochures. Detailed individual activities stay.
"""
from __future__ import annotations
import datetime as dt
import re
import unicodedata

GENERIC_PREFIXES=(
 "programacion ", "programa de actividades", "calendario de actividades",
 "agenda de actividades", "cursos y talleres", "nuevas actividades de",
 "actividades de la concejalia", "fiestas de san rafael 2026",
 "fiestas patronales de", "programa de fiestas",
)
SPECIFIC_PROGRAM_TITLES=(
 "el ayuntamiento de agaete pone en marcha el programa de talleres",
 "talleres de bienestar emocional y envejecimiento activo",
)

def normalized(title):
 s=unicodedata.normalize("NFKD",str(title or "")).casefold()
 return "".join(c for c in s if not unicodedata.combining(c)).strip(' «"')

def is_multi_activity(event):
 title=normalized(event.get("title"))
 if any(title.startswith(p) for p in SPECIFIC_PROGRAM_TITLES):return True
 if not any(title.startswith(p) for p in GENERIC_PREFIXES):return False
 # Single-day named festivals/cultural performances should not be removed
 # just because a title contains "fiestas".
 if title.startswith(("programacion ","cursos y talleres","nuevas actividades")):
  return True
 raw_start=str(event.get("start") or "")[:10]
 raw_end=str(event.get("end") or raw_start)[:10]
 try:
  duration=(dt.date.fromisoformat(raw_end)-dt.date.fromisoformat(raw_start)).days
 except ValueError:return False
 venue=normalized(event.get("venue"))
 unspecified=(not venue or venue.startswith(("consultar","recinto por confirmar","lugar pendiente","municipio por confirmar")))
 return duration>=2 and unspecified

def is_non_event_listing(event):
 """A reservation for use of a facility is not an organized activity.

 This deliberately narrow rule avoids excluding actual ticketed events or
 activities whose titles merely mention booking or registration.
 """
 title=normalized(event.get("title"))
 return bool(re.match(r"^reservas?(?:\s+de)?\s+(?:area|areas)\s+recreativas?\b",title))

def filter_public_plans(events):
 accepted=[]
 needs_review=[]
 for e in events:
  is_program=is_multi_activity(e)
  is_facility=is_non_event_listing(e)
  if is_program or is_facility:
   needs_review.append({
    "id":e.get("id"),"title":e.get("title"),"start":e.get("start"),
    "end":e.get("end"),"municipality":e.get("municipality"),
    "source_name":e.get("source_name"),"source_url":e.get("source_url"),
    "reason":("Programa con varias actividades: desglosar por fecha, hora y recinto"
              if is_program else "Reserva administrativa de una instalación, no un evento")
   })
  else:accepted.append(e)
 return accepted,needs_review
