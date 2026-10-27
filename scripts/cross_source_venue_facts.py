"""Conservative recovery of missing event venues from an independent source.

Only exact normalized event title, same island municipality and same start day.
The corroborating event must be independently published (different source) and
have a specific non-vague venue; known conflicting venues/times block recovery.
No fuzzy matching, title guessing, venue coordinates or external requests.
"""
from __future__ import annotations
from collections import defaultdict
import venue_quality

def norm(s):
    import re,unicodedata
    value=unicodedata.normalize("NFKD",str(s or "").casefold())
    value="".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+","",value)
def changed_time(e,other):
    start=str(e["start"] or "")
    other_start=str(other["start"] or "")
    return len(start)>=16 and len(other_start)>=16 and start[11:16]!=other_start[11:16]
def enrich(conn,now,today):
    rows=[dict(x) for x in conn.execute(
        """SELECT id,title,start,"end",municipality,venue,source_name,source_url
           FROM events WHERE status='approved'
           AND substr(COALESCE("end",start),1,10)>=?""",(today.isoformat(),))]
    groups=defaultdict(list)
    for row in rows:
        k=(norm(row["title"]),norm(row["municipality"]),row["start"][:10])
        groups[k].append(row)
    examined=verified=ambiguous=0
    for entries in groups.values():
        missing=[x for x in entries if not venue_quality.named_venue(x)]
        confirmed=[x for x in entries if venue_quality.named_venue(x)]
        if not (missing and confirmed):continue
        for target in missing:
            examined+=1
            # Require independent source and compatible explicit start times.
            candidates=[x for x in confirmed
                        if x["source_name"]!=target["source_name"] and
                        x["source_url"]!=target["source_url"] and
                        not changed_time(x,target)]
            # A second candidate with a conflicting venue, even from the same
            # source, means we cannot choose the right location for this date.
            all_confirmed_names={norm(x["venue"]) for x in confirmed}
            possible={norm(x["venue"]):x["venue"] for x in candidates}
            if len(possible)!=1 or len(all_confirmed_names)!=1:
                ambiguous+=1
                continue
            venue=next(iter(possible.values()))
            conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                         (venue,now,target["id"]))
            verified+=1
    return {"inspected":examined,"verified":verified,"left_ambiguous":ambiguous}
