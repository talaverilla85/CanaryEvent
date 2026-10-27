"""Curated, verified venues for stable event geolocation in Gran Canaria.

No online geocoding during the daily sync. The coordinates were individually
checked against name-matched OpenStreetMap POIs (27 Oct 2026) and institutional
street addresses. Keep exact municipality in each key to avoid homonyms.
An unknown, vague, or multi-location venue falls back to the municipality.
These are venue/map reference points, not verified entrance coordinates.
"""
from __future__ import annotations
import re
import unicodedata

# Coordinates from individually inspected, same-name OpenStreetMap venue POIs.
# OSM references identify the exact nodes/ways independently of this parser.
# Official venues' contact/location pages support building identity.
VENUES = (
    ("Las Palmas de Gran Canaria", "Sala Insular de Teatro", 28.1073434, -15.4208720,
     "https://www.openstreetmap.org/node/10269622609",
     "https://salainsulardeteatro.com/localizacion.html"),
    ("Las Palmas de Gran Canaria", "Auditorio Alfredo Kraus", 28.1302128, -15.4490139,
     "https://www.openstreetmap.org/way/585709389",
     "https://auditorioalfredokraus.es/contacto"),
    ("Las Palmas de Gran Canaria", "Centro Comercial Siete Palmas", 28.0975186, -15.4558536,
     "https://www.openstreetmap.org/way/31508308",
     "https://www.laspalmasgc.es/es/la-ciudad/la-ciudad-comercial/centros-comerciales-y-de-ocio/"),
    ("Las Palmas de Gran Canaria", "Teatro Guiniguada", 28.1017377, -15.4149715,
     "https://www.openstreetmap.org/way/259746867",
     "https://www3.gobiernodecanarias.org/cultura/ocio/teatroguiniguada/contacto/"),
    ("Las Palmas de Gran Canaria", "Teatro Pérez Galdós", 28.1035634, -15.4140057,
     "https://www.openstreetmap.org/way/251657540",
     "https://www.laspalmasgc.es/es/ayuntamiento/organismos-y-empresas/teatro-perez-galdos/"),
    ("Las Palmas de Gran Canaria", "Museo Elder", 28.1412306, -15.4296613,
     "https://www.openstreetmap.org/node/335686723",
     "https://www.museoelder.org/"),
    ("Las Palmas de Gran Canaria", "Gran Canaria Arena", 28.1030082, -15.4569380,
     "https://www.openstreetmap.org/way/289163235",
     "https://www.grancanariaarena.com/"),
)

def normalize(value: str) -> str:
    value=unicodedata.normalize("NFKD", str(value or "")).casefold()
    value="".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+"," ",value).strip()

# Only exact normalized names, plus independently verified equivalent public
# names. No substring / fuzzy matching: complex cultural centers often contain
# multiple stages and entrance points.
ALIASES = {
    ("Las Palmas de Gran Canaria","Museo Elder de la Ciencia y la Tecnología"):
      "Museo Elder",
    ("Las Palmas de Gran Canaria","CC Siete Palmas"):
      "Centro Comercial Siete Palmas",
    ("Las Palmas de Gran Canaria","Centro Comercial 7 Palmas"):
      "Centro Comercial Siete Palmas",
}

INDEX={(normalize(m),normalize(v)):(lat,lon,osm,official)
       for m,v,lat,lon,osm,official in VENUES}
for (municipality,alias),official_name in ALIASES.items():
    INDEX[(normalize(municipality),normalize(alias))]=INDEX[(normalize(municipality),normalize(official_name))]

def find(municipality,venue):
    """Return venue coordinate tuple or None; never guess unknown recintos."""
    if not municipality or not venue:return None
    value=normalize(venue)
    if not value or any(v in value for v in ("consultar el recinto","recinto por confirmar","lugar por confirmar")):
        return None
    return INDEX.get((normalize(municipality),value))

def resolve(municipality,venue,places):
    if municipality not in places:raise KeyError("Unknown municipality")
    result=find(municipality,venue)
    if result:
        return result[0],result[1],"venue"
    lat,lon=places[municipality]
    return lat,lon,"municipality"

def backfill(conn,places):
    """Recompute geolocation for old and new rows without resetting event IDs.

    A later official venue correction also changes the coordinates here.
    Only location-related columns are updated, preserving all verified other
    fields, previous date/source/approval state and event identity.
    """
    changed=0
    rows=conn.execute("SELECT id,municipality,venue,lat,lng,accuracy FROM events").fetchall()
    for row in rows:
        id,muni,venue,old_lat,old_lng,old_accuracy=row
        if muni not in places:continue
        lat,lng,accuracy=resolve(muni,venue,places)
        if (old_lat,old_lng,old_accuracy)!=(lat,lng,accuracy):
            conn.execute("UPDATE events SET lat=?,lng=?,accuracy=? WHERE id=?",
                         (lat,lng,accuracy,id))
            changed+=1
    return changed
