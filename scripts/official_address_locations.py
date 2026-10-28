"""Verified address signatures from original institutional event descriptions.

This is deliberately conservative: a museum/library name in a flyer alone
may refer to the *organizer*, not its venue. Require exact venue name, street
address and Gran Canaria postcode in one official event information panel.
The signatures are independent of the Cabildo's abbreviated JSON-LD.
They never supply unverified GPS coordinates.
"""
import re
import unicodedata

PROFILES=(
    {
       "municipality":"Las Palmas de Gran Canaria",
       "venue":"Biblioteca Insular de Gran Canaria",
       "address":r"\bRemedios\s*,\s*7\b",
       "postcode":"35002",
    },
    {
       "municipality":"Moya",
       "venue":"Casa-Museo Tomás Morales",
       "address":r"\bPlaza\s+Tom[aá]s\s+Morales\s*,\s*s\s*/\s*n\b",
       "postcode":"35420",
    },
)

def norm(text):
    s=unicodedata.normalize("NFKD",str(text or ""))
    return " ".join("".join(x for x in s if not unicodedata.combining(x)).casefold().split())

def from_official_address(description,municipality):
    if not isinstance(description,str) or not description:return ""
    # This is an address signature, not a fuzzy venue/organizer name lookup.
    matches=[]
    for p in PROFILES:
        if norm(municipality)!=norm(p["municipality"]):continue
        v=re.search(re.escape(p["venue"]),description,re.I)
        if not v:continue
        # Street+postcode must follow that precise place within one compact
        # address block; unrelated references elsewhere do not count.
        address=description[v.end():v.end()+130]
        matched=re.search(p["address"],address,re.I)
        if not matched:continue
        trailer=address[matched.end():matched.end()+45]
        if not re.search(r"\b"+p["postcode"]+r"\b",trailer):continue
        matches.append(p["venue"])
    return matches[0] if len(matches)==1 else ""
