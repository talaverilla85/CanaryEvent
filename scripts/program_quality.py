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

MONTHS = {
 "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
 "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
 "noviembre":11,"diciembre":12,
}
REGISTRATION_DEADLINE = re.compile(
 r"\binscripci(?:on|ones)\b.{0,125}?"
 r"(?:\bhasta\s+(?:el\s+)?|\bdel\s+\d{1,2}\s+al\s+)"
 r"(\d{1,2})\s+de\s+("
 + "|".join(MONTHS)
 + r")(?:\s+de\s+(\d{4}))?",
 re.I,
)

def public_access_blocker(event, today=None):
 """Exclude only demonstrably unavailable public participation.

 Do not exclude a paid event, an age-targeted event, or an activity that
 merely requests reservations. If membership is prioritised and public
 attendance relies on unconfirmed spare places, it is not an openly
 actionable D'Parranda plan.
 """
 if today is None: today=dt.date.today()
 details=normalized(event.get("details"))
 if not details:return ""
 conditional_public=(
     re.search(r"\bsi\s+(?:aun\s+)?quedan\s+plazas\b",details)
     and re.search(r"\bpublico\s+(?:en\s+)?general\b",details)
     and re.search(r"\b(?:socios?|soci@s|miembros)\b",details)
 )
 if conditional_public:
     return "Acceso al público general condicionado a plazas para socios, sin disponibilidad confirmada"
 if re.search(r"\b(?:solo|unicamente|exclusivamente)\s+(?:para\s+)?(?:socios|soci@s|miembros)\b",details):
     return "Acceso limitado exclusivamente a socios o miembros"
 match=REGISTRATION_DEADLINE.search(details)
 if match:
     day=int(match.group(1))
     month=MONTHS[match.group(2).casefold()]
     year=int(match.group(3) or str(event.get("start") or "")[:4] or today.year)
     try:limit=dt.date(year,month,day)
     except ValueError:return ""
     if limit<today:
         return "Inscripción cerrada según el plazo expreso de la fuente oficial"
 return ""

def filter_public_plans(events,today=None):
 accepted=[]
 needs_review=[]
 for e in events:
  is_program=is_multi_activity(e)
  is_facility=is_non_event_listing(e)
  access_blocker=public_access_blocker(e,today)
  if is_program or is_facility or access_blocker:
   needs_review.append({
    "id":e.get("id"),"title":e.get("title"),"start":e.get("start"),
    "end":e.get("end"),"municipality":e.get("municipality"),
    "source_name":e.get("source_name"),"source_url":e.get("source_url"),
    "reason":("Programa con varias actividades: desglosar por fecha, hora y recinto"
              if is_program else "Reserva administrativa de una instalación, no un evento" if is_facility else access_blocker)
   })
  else:accepted.append(e)
 return accepted,needs_review
