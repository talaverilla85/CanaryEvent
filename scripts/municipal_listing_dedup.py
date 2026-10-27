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
 "Ayuntamiento de Ingenio",
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
def same_verified_venue(a,b,norm,municipality):
    """Strong venue match only; never infer that two different halls coincide."""
    aa=norm(a or "")
    bb=norm(b or "")
    if not aa or not bb:return False
    if aa==bb:return True
    # The municipal Gáldar culture programme spells Guaires in the venue,
    # whereas the Cabildo uses Guaire. Both refer to the same named centre.
    if norm(municipality)==norm("Gáldar"):
        aliases={norm("Centro Cultural Guaire"),norm("Centro Cultural Guaires")}
        if {aa,bb}==aliases:return True
    # A venue may include a *specific postal address* appended as a subtitle.
    # Do not allow arbitrary prefix matches: they can be separate stages.
    left=str(a or "").split(" · ",1)
    right=str(b or "").split(" · ",1)
    if len(left)>1 and norm(left[0])==bb and any(
        x in norm(left[1]) for x in ("calle","avenida","carretera","plaza","numero")):
        return True
    if len(right)>1 and norm(right[0])==aa and any(
        x in norm(right[1]) for x in ("calle","avenida","carretera","plaza","numero")):
        return True
    return False

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
    # Reconcile duplicate factual entries from *any* official pair or even
    # duplicate indexed Cabildo URLs, but only when exact session times and
    # named venues agree. This conservatively handles Juventud/Cabildo,
    # official municipal event pages and double-indexed performances.
    for group in groups.values():
        remaining=[e for e in group if e["id"] not in eliminated]
        if len(remaining)<2:continue
        for i,a in enumerate(remaining):
            if a["id"] in eliminated:continue
            for b in remaining[i+1:]:
                if b["id"] in eliminated:continue
                if not (is_clock(a.get("start")) and is_clock(b.get("start"))):continue
                if a["start"][11:16]!=b["start"][11:16]:continue
                if not (is_known_venue(a.get("venue")) and is_known_venue(b.get("venue"))):
                    continue
                if not same_verified_venue(a["venue"],b["venue"],norm,a["municipality"]):
                    continue
                winner=max((a,b),key=lambda e:(score(e),-int(e["id"])))
                eliminated.add(b["id"] if winner is a else a["id"])
                if a["id"] in eliminated:break
    # First-party Circuito de Artes Escénicas advertises the definitive hall
    # and session time for its own productions. The Cabildo aggregator can
    # repeat the same show with a wrong hall or an unknown time. Prefer the
    # exact named organizer's event page; leave its Cabildo record in SQLite.
    # Never apply this trust to unapproved domains or conflicting known hours.
    for group in groups.values():
        originals=[e for e in group
                   if str(e.get("source_name") or "")=="Circuito de Artes Escénicas GC"
                   and str(e.get("source_url") or "").startswith(
                       "https://artesescenicasgrancanaria.com/evento-")
                   and is_known_venue(e.get("venue")) and is_clock(e.get("start"))]
        aggregates=[e for e in group
                    if str(e.get("source_name") or "").startswith(CABILDO_PREFIX)]
        for official in originals:
            for aggregate in aggregates:
                if official["id"] in eliminated or aggregate["id"] in eliminated:continue
                if (is_clock(aggregate.get("start")) and
                    aggregate["start"][11:16]!=official["start"][11:16]):
                    continue
                eliminated.add(aggregate["id"])
    return [e for e in events if e["id"] not in eliminated]
