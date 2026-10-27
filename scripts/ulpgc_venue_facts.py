"""Conservative venue/time corrections for ULPGC blood donation events.

The municipal Cabildo listing often displays the END TIME as the event
start, while the organizer gives distinct daily opening hours.
Never infer individual daily sessions or coordinates from a title.
This module is a pure-data parser: no network requests are made to ULPGC,
which currently returns HTTP 403 to programmatic requests.
"""
from __future__ import annotations
from urllib.parse import urlsplit
import re

PREFIX="Campaña de hemodonación:"
VENUE_PREFIXES=(
    "Facultad de ","Escuela de ","Escuela Universitaria ","Edificio de ",
    "Parque Científico y Tecnológico",
)
VERIFIED_TIMETABLE={
    # ULPGC user-provided official event listing + Canary Govt 23 Oct 2026.
    ("campana de hemodonacion: facultad de ciencias del mar","2026-10-27"):
    ("2026-10-27T09:00:00","2026-10-27T18:30:00",
     "26 oct: 09:30–19:45; 27 oct: 09:00–18:30.")
}

def normalized(text):
    import unicodedata
    plain=unicodedata.normalize("NFKD",str(text or ""))
    return re.sub(r"\s+"," ", "".join(c for c in plain if not unicodedata.combining(c)).lower()).strip()

def safe_organizer(url):
    try:
        u=urlsplit(url)
        return (u.scheme=="https" and u.hostname in ("ulpgc.es","www.ulpgc.es")
                and bool(re.fullmatch(r"/agenda/20\d{2}/\d{2}/\d{2}/[a-z0-9-]+",u.path))
                and not u.query and not u.fragment)
    except (TypeError,ValueError):
        return False

def enhance(entry):
    """Return a copy; only enrich organizer-confirmed ULPGC donation listings."""
    e=dict(entry)
    title=str(e.get("title") or "")
    if not safe_organizer(e.get("organizer_url")) or not normalized(title).startswith(normalized(PREFIX)):
        return e
    venue_from_title=title.split(":",1)[-1].strip()[:150]
    if not (5<len(venue_from_title)<150 and
            any(venue_from_title.startswith(p) for p in VENUE_PREFIXES)):
        return e

    if not e.get("venue") or e["venue"].lower().startswith(("consultar","recinto por confirmar")):
        e["venue"]=venue_from_title

    key=(normalized(title),str(e.get("start") or "")[:10])
    if key in VERIFIED_TIMETABLE:
        start,end,summary=VERIFIED_TIMETABLE[key]
        e["start"]=start;e["end"]=end
        e["details"]="Facultad de Ciencias del Mar (Campus de Tafira). "+summary+" Horarios verificados en la convocatoria de 2026; comprueba posibles cambios en el enlace oficial."
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",str(e.get("start"))):
        # A Cabildo end timestamp is not an opening time. Preserve the day.
        e["start"]=e["start"][:10]
        e["end"]=None
        if not e.get("details") or "Consulta el recinto" in e["details"]:
            e["details"]="Campaña de donación de sangre en "+venue_from_title+". Consulta los horarios específicos de cada jornada en la web de la ULPGC."
    if e.get("category")=="ocio":
        e["category"]="otros"
    return e
