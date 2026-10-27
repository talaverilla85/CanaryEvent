"""Publish only events for which the visitor can identify an actual venue.

Events remain in SQLite for further enrichment. The public catalogue must not
confuse a municipality centroid, a generic area or an organizer with a venue.
"""
import re
import unicodedata

UNVERIFIED=("consultar el recinto","recinto por confirmar","lugar por confirmar",
            "ubicación por confirmar","por determinar","pendiente de confirmar",
            "varios emplazamientos","diferentes espacios","varias ubicaciones")
VAGUE={"centro cultural","biblioteca municipal","teatro","sala","plaza",
       "centro municipal","lugar por confirmar","recinto ferial",
       "diferentes emplazamientos","varios lugares","por determinar"}

def norm(value):
    value=unicodedata.normalize("NFKD",str(value or "").casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())

def named_venue(event):
    venue=norm(event.get("venue"))
    town=norm(event.get("municipality"))
    if len(venue)<5 or venue==town or venue in VAGUE:return False
    if any(venue.startswith(p) for p in UNVERIFIED):return False
    # "Sala de exposiciones Lola Massieu" is a building; "Las Palmas"
    # alone is not. Do not require a specific naming convention for venues.
    if re.fullmatch(r"(?:en|a)\s+.+",venue):return False
    return True

def split_verified(events):
    confirmed,review=[],[]
    for e in events:
        if named_venue(e):
            confirmed.append(e)
        else:
            review.append({
                "id":e.get("id"),"title":e.get("title"),"start":e.get("start"),
                "end":e.get("end"),"municipality":e.get("municipality"),
                "venue":e.get("venue"),"source_name":e.get("source_name"),
                "source_url":e.get("source_url"),"organizer_url":e.get("organizer_url"),
                "reason":"Falta confirmar recinto concreto, no solo municipio"})
    return confirmed,review
