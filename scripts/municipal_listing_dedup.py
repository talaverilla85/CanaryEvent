"""Conservative export-time reconciliation of Cabildo vs municipal events.

A Cabildo entry may have a source-specific primary key, so SQLite keeps both
original records for traceability. Export avoids double cards only when the
municipal and Cabildo listings agree on normalized title, municipality and
calendar date, without contradictory exact session times/known venues.
"""
from collections import defaultdict

MUNICIPAL_PREFIXES=(
 "Ayuntamiento de Santa Brígida",
 "Ayuntamiento de Arucas",
 "Ayuntamiento de Teror",
 "Ayuntamiento de Artenara",
 "Ayuntamiento de Telde",
)
CABILDO_PREFIX="Portal oficial de Eventos Gran Canaria"
def is_known_venue(text):
    val=(text or "").strip()
    return bool(val) and not val.lower().startswith(("consultar","por confirmar","pendiente"))
def is_clock(text):
    return bool(text and len(text)>10 and "T" in text)
def safe_same_program(a,b,norm):
    if is_clock(a.get("start")) and is_clock(b.get("start")):
        if a["start"][11:16]!=b["start"][11:16]:return False
    if is_known_venue(a.get("venue")) and is_known_venue(b.get("venue")):
        if norm(a["venue"])!=norm(b["venue"]):return False
    return True
def score(e):
    return (
        int(is_clock(e.get("start")))*8+
        int(is_known_venue(e.get("venue")))*3+
        int(bool(e.get("price") or e.get("free")==1))*3+
        int(bool(e.get("image_url")))*2+
        int(str(e.get("source_name") or "").startswith(MUNICIPAL_PREFIXES))
    )
def reconcile(events,norm):
    groups=defaultdict(list)
    for e in events:
        title_key=norm(e["title"])
        # Both official sites refer to the same market, with a shortened title.
        # Narrow this alias to its exact day and town; never merge annually or
        # conflate other markets with different dates or venues.
        if (norm(e["municipality"])==norm("Artenara")
            and str(e["start"])[:10]=="2026-10-31"
            and title_key in (norm("II Mercadillo Tradicional · Artenara"),
                              norm("II Edición del Mercadillo Tradicional de Artenara"))):
            title_key=norm("II Edición del Mercadillo Tradicional de Artenara")
        groups[(title_key,str(e["start"])[:10],norm(e["municipality"]))].append(e)
    eliminated=set()
    for group in groups.values():
        if len(group)<2:continue
        muni=[e for e in group if str(e.get("source_name") or "").startswith(MUNICIPAL_PREFIXES)]
        cab=[e for e in group if str(e.get("source_name") or "").startswith(CABILDO_PREFIX)]
        for municipal in muni:
            for other in cab:
                if municipal["id"] in eliminated or other["id"] in eliminated:continue
                if not safe_same_program(municipal,other,norm):continue
                winner=max((municipal,other),key=lambda e:(score(e),-int(e["id"])))
                loser=other if winner is municipal else municipal
                eliminated.add(loser["id"])
    return [e for e in events if e["id"] not in eliminated]
