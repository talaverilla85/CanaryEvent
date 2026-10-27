"""Conservative venue recognition from the organizer's own event description.

This is *not* geocoding. A named venue improves the public card, but leaves
coordinate accuracy at the municipality until independently validated.
"""
from __future__ import annotations
import html
import re
import unicodedata
from bs4 import BeautifulSoup

# A location must name an actual place, not merely an organization or town.
PLACE_TYPE = (
    r"biblioteca|centro(?:\s+(?:cultural|de\s+arte|cívico|municipal|de\s+mayores))?"
    r"|casa(?:\s+(?:de\s+la\s+cultura|de\s+la\s+juventud|gourié))?"
    r"|museo|teatro|auditorio|sala|plaza|parque|pabellón|recinto"
    r"|espacio|club|salón|estadio|colegio|instituto|universidad"
    r"|ermita|iglesia|local|polideportivo|anfiteatro|centro\s+de\s+interpretación"
)
TYPE_START = re.compile(r"^(?:" + PLACE_TYPE + r")\b", re.I)
DIRECT = re.compile(
    r"(?:lugar|ubicación|recinto|punto\s+de\s+encuentro|sede)"
    r"\s*(?:\:|：|–|-)\s*([^\n\r;.!?]{4,125})", re.I
)
PIN = re.compile(r"📍\s*([^\n\r;.!?]{4,125})", re.I)
CONTEXT = re.compile(
    r"\ben\s+(?:(?:la|el)\s+planta\s+baja\s+de\s+)?"
    r"(?:el|la|los|las)\s+[«“\"']?"
    r"((?:" + PLACE_TYPE + r")\b[^\n\r,;.!?]{3,110})", re.I
)
BREAK = re.compile(
    r"\s+(?:Información|Inscripción|Inscripciones|Horario|Horarios|Precio|Entradas|Contacto"
    r"|Teléfono|Aforo|Reservas|Fecha|Más\s+información|Organiza|Organizador|Elige|Grupo\s+\d+)\s*[:\-]?"
    r"|\s+(?:donde|durante|para|contaremos|tendremos|que\s+se|con\s+una|con\s+el|con\s+la|o\s+llamando)\b",
    re.I,
)
GENERIC = {"centro", "biblioteca", "museo", "teatro", "casa", "plaza", "parque",
           "sala", "recinto", "club", "local", "sede", "auditorio"}
MULTIPLE = re.compile(r"\b(?:sedes|varios\s+(?:lugares|recintos|espacios)|diferentes\s+(?:espacios|lugares))\b",re.I)


def normalize(text):
    t=unicodedata.normalize("NFKD",str(text or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


def _clean(value, municipality):
    t=" ".join(value.replace("\xa0"," ").split())
    t=BREAK.split(t,maxsplit=1)[0]
    t=re.split(r"[,|•]|\s+[—–]\s+|https?://",t,maxsplit=1)[0]
    t=t.strip(" :–-·,.'\"“”«»()")
    if len(t)<8 or len(t)>95 or not TYPE_START.match(t):
        return ""
    # Do not publish incomplete, cut-off snippets such as "Biblioteca M".
    if re.search(r"\s+[A-ZÁÉÍÓÚÑ]$",t):return ""
    n=normalize(t)
    if n==normalize(municipality) or n in GENERIC:
        return ""
    # Distinguish a named building from a vague statement like "Centro cultural".
    if n in ("centro cultural", "centro municipal", "biblioteca municipal", "casa de la cultura",
             "sala de actos", "plaza del pueblo", "punto de encuentro"):
        return ""
    # A list of venues must never be represented as one exact venue.
    if re.search(r"\s+(?:y|o)\s+(?:el|la|los|las)?\s*(?:"+PLACE_TYPE+r")\b",t,re.I):
        return ""
    return t


def from_description(description,municipality):
    """Return only one clearly identified venue, or empty on ambiguity.

    Primary evidence: explicit 'Lugar:' / a map-pin marker. Secondary evidence:
    a named building in the phrase 'en el/la ...'. A mere reference to the
    organizer, a municipality or several possible locations is not sufficient.
    """
    if not description or not isinstance(description,str):return ""
    text=unicodedata.normalize("NFKC",html.unescape(description[:12000]))
    soup=BeautifulSoup(text,"html.parser")
    text=soup.get_text("\n",strip=True)
    text=re.sub(r"[ \t]+"," ",text)
    direct=[]
    for rx in (DIRECT,PIN):
        for m in rx.finditer(text):
            candidate=_clean(m.group(1),municipality)
            if candidate:direct.append(candidate)
    # If the official description names *several* spaces, do not choose one.
    contextual=[]
    for match in CONTEXT.finditer(text):
        candidate=_clean(match.group(1),municipality)
        if candidate:contextual.append(candidate)
    all_names=direct+contextual
    unique={normalize(v):v for v in all_names}
    if len(unique)>1:return ""
    if not unique:return ""
    if MULTIPLE.search(text) and not direct:
        return ""
    if re.search(r"\b(?:en\s+(?:cuatro|tres|\d+)\s+formatos|\d+\s+talleres.{0,90}\d+\s+sesiones)\b",text,re.I):
        return ""
    return next(iter(unique.values()))
