"""Exclude routine multiplex screenings while preserving cinema as a cultural plan.

The official Cabildo feed contains scheduled regular multiplex movie entries,
sometimes labelled "ocio" and sometimes "cultura". A venue-based guard with
explicit cultural/one-off exceptions is safer than suppressing the word "cine"
or the full "cultura" category. Keep original DB records for traceability.
"""
from __future__ import annotations
import re
import unicodedata

# Exact verified multiplex venue and cinema chains. A venue called "El Cine"
# may be a performing-arts cultural centre: never block on the word cine alone.
MULTIPLEX_VENUES = (
    "centro comercial siete palmas",
    "cinesa",
    "ocine",
    "multicines",
    "yelmo cine",
    "cines yelmo",
    "cine yelmo",
    "cineplex",
)
CULTURAL_EXCEPTIONS = (
    r"\b(efecto cinema|ciclo de cine|ciclo cinematografico|cineclub|cine forum|cineforum)\b",
    r"\b(festival de cine|film fest|muestra de cine|cine de verano|cine al aire libre)\b",
    r"\b(preestreno|pre estreno|estreno especial|proyeccion especial|pase unico)\b",
    r"\b(coloquio|cine con debate|presentacion con el director|sesion unica)\b",
    r"\b(live viewing|retransmision en directo|concierto en directo en cines)\b",
)
CLEAR_NON_MOVIE_TERMS = (
    r"\b(feria|mercado|taller|exposicion|conferencia|cuentacuentos)\b",
    r"\b(romeria|verbena|fiestas patronales|encuentro vecinal|campamento)\b",
    r"\b(carrera|concierto presencial|visita guiada)\b",
)
CABILD_SOURCE="Portal oficial de Eventos Gran Canaria"

def norm(text):
    a=unicodedata.normalize("NFKD",str(text or ""))
    return "".join(c for c in a if not unicodedata.combining(c)).casefold()

def is_commercial_screening(event):
    """True only for high-confidence routine movie sessions."""
    source=str(event.get("source_name") or "")
    if not source.startswith(CABILD_SOURCE):
        return False
    venue=norm(event.get("venue"))
    if not any(name in venue for name in MULTIPLEX_VENUES):
        return False
    title=norm(event.get("title"))
    if any(re.search(p,title) for p in CULTURAL_EXCEPTIONS):
        return False
    if any(re.search(p,title) for p in CLEAR_NON_MOVIE_TERMS):
        return False
    return True

def remove_commercial_screenings(events):
    kept=[]
    excluded=[]
    for event in events:
        if is_commercial_screening(event):
            excluded.append(event)
        else:
            kept.append(event)
    return kept,excluded
