"""Reconcile Cabildo copies with exact first-party Teatro Cuyás listings.

The official Cuyás and Circuito programmes already produce verified,
individually dated theatre sessions. A Cabildo copy often links the same
event id on another sister venue's website, which *does not* mean that
sister venue hosts the show. Recover only when:
- the exact original shared CMS event numeric id agrees;
- normalized full title and municipality agree;
- the secondary calendar-day interval exactly equals the set of
  independently published show days;
- any published clock time agrees with the official show on that day.
No arbitrary URL scraping, fuzzy titles, mismatched dates or schedules.
This is provenance enrichment, not new event discovery.
"""
from __future__ import annotations
import datetime as dt
import re
import unicodedata
from collections import defaultdict
import venue_quality

NAME="Cuyás · reconciliación con programas originales"
OFFICIAL_RE=re.compile(r"^https://(?:teatrocuyas\.com|artesescenicasgrancanaria\.com)/evento-([1-9]\d*)-[a-z0-9-]+\.html$")
COPY_RE=re.compile(r"^https://(?:salainsulardeteatro\.com|teatrocuyas\.com|artesescenicasgrancanaria\.com)/evento-([1-9]\d*)-[a-z0-9-]+\.html$")
CABILDO="Portal oficial de Eventos Gran Canaria"
OFFICIAL_SOURCES=("Teatro Cuyás · agenda oficial","Circuito de Artes Escénicas GC")
THEATRE="Teatro Cuyás"
CITY="Las Palmas de Gran Canaria"

def norm(s):
    raw=unicodedata.normalize("NFKD",str(s or "").casefold())
    return "".join(x for x in raw if x.isalnum() and not unicodedata.combining(x))

def date_span(start,end,limit=7):
    try:
        first=dt.date.fromisoformat(str(start or "")[:10])
        last=dt.date.fromisoformat(str(end or start or "")[:10])
    except ValueError:return set()
    if last<first or (last-first).days>limit:return set()
    return {(first+dt.timedelta(days=k)).isoformat() for k in range((last-first).days+1)}

def corroborate(originals,target):
    link=COPY_RE.fullmatch(str(target.get("organizer_url") or ""))
    if not link or not str(target.get("source_name","")).startswith(CABILDO):
        return ""
    if target.get("municipality")!=CITY or venue_quality.named_venue(target):
        return ""
    candidates=originals.get(link.group(1),[])
    if not candidates:
        return ""
    title=norm(target.get("title"))
    if len(title)<15:return ""
    if any(norm(row["title"])!=title or row["municipality"]!=CITY
           or norm(row["venue"])!=norm(THEATRE) for row in candidates):
        return ""
    official_days={row["start"][:10] for row in candidates}
    target_days=date_span(target.get("start"),target.get("end"))
    if not target_days or official_days!=target_days:
        return ""
    start=str(target.get("start") or "")
    if len(start)>=16 and any(row["start"][:10]==start[:10]
                             and row["start"][11:16]!=start[11:16] for row in candidates):
        return ""
    return THEATRE

def enrich(conn,now,today):
    rows=[dict(x) for x in conn.execute(
        """SELECT id,title,start,"end",municipality,venue,source_name,
                  source_url,organizer_url FROM events WHERE status='approved'
           AND substr(COALESCE("end",start),1,10)>=?""",(today.isoformat(),))]
    originals=defaultdict(list)
    for e in rows:
        if e["source_name"] not in OFFICIAL_SOURCES:
            continue
        match=OFFICIAL_RE.fullmatch(str(e["source_url"] or ""))
        if match and venue_quality.named_venue(e) and e["municipality"]==CITY and len(str(e["start"]))>=16:
            originals[match.group(1)].append(e)
    checked=changed=0
    for e in rows:
        if not str(e["source_name"]).startswith(CABILDO) or venue_quality.named_venue(e):
            continue
        if not COPY_RE.fullmatch(str(e.get("organizer_url") or "")):
            continue
        checked+=1
        verified=corroborate(originals,e)
        if verified:
            conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                         (verified,now,e["id"]))
            changed+=1
    conn.commit()
    return {"source":NAME,"checked_at":now,"found":checked,"added":0,
            "changed":changed,"error":""}


def exclude_conflicting_sister_venue(events):
    '''Quarantine Cabildo claims of a Sala Insular show when the same long,
    exact named performance is confirmed by the primary Cuyás source for
    that same day. Keep SQLite source for audit; do not generate a false
    extra date from its Cabildo end-date.
    This narrowly targets two sister theatre venues that share CMS ids.
    '''
    cuyas=defaultdict(list)
    for row in events:
        page=OFFICIAL_RE.fullmatch(str(row.get("source_url") or ""))
        if page and row.get("source_name") in OFFICIAL_SOURCES and (
            norm(row.get("venue"))==norm(THEATRE)) and row.get("municipality")==CITY:
            cuyas[(norm(row["title"]),row["start"][:10])].append(row)
    kept=[]
    conflicts=[]
    for row in events:
        name=norm(row.get("title"))
        key=(name,str(row.get("start") or "")[:10])
        is_sister=(row.get("source_name","").startswith(CABILDO)
            and row.get("municipality")==CITY
            and norm(row.get("venue"))==norm("Sala Insular de Teatro")
            and len(name)>=20
            and cuyas.get(key))
        if is_sister:
            # The Cabildo claims the *other* theatre for a confirmed
            # first-party performance. Quarantine the secondary copy
            # rather than issue a third/phantom show.
            conflicts.append({
                "id":row["id"],"title":row["title"],
                "source_url":row["source_url"],
                "claimed_venue":row["venue"],
                "verified_venue":THEATRE,
                "reason":"conflicting_sister_theatre",
            })
        else:
            kept.append(row)
    return kept,conflicts
