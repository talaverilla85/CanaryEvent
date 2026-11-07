"""Calculate real public-catalog changes between successful synchronizations.

Source-level 'added'/'changed' counters are *not* proof that an event was
published. Compare the exported public list by its stable event ID instead.
"""
from __future__ import annotations

import json
import re
import unicodedata
import datetime as dt
from zoneinfo import ZoneInfo
from collections import Counter
from pathlib import Path


def read_published(path):
    """Return the previous public list, or None when no valid baseline exists."""
    try:
        content=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError,ValueError,TypeError):
        return None
    if not isinstance(content,dict) or not isinstance(content.get("events"),list):
        return None
    if not all(isinstance(event,dict) for event in content["events"]):
        return None
    return content["events"]


def _indexed(rows):
    indexed={}
    for item in rows:
        if not isinstance(item,dict):
            continue
        event_id=item.get("id")
        if isinstance(event_id,bool) or not isinstance(event_id,(str,int)):
            continue
        # Never treat transient export metadata as a user-visible edit.
        details={key:value for key,value in item.items()
                 if key not in ("generated_at","updated_at","last_seen")}
        indexed[str(event_id)]=details
    return indexed


def _day(value):
    text=str(value or "")[:10]
    return text if re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}",text) else None


def _normalized(value):
    text=unicodedata.normalize("NFKD",str(value or "").casefold())
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c))


def _identity(event):
    """Conservative, source-independent match for a reissued event listing."""
    key=(_normalized(event.get("title")),_day(event.get("start")),
         _normalized(event.get("municipality")),_normalized(event.get("venue")))
    return key if all(key) else None


def compare_public_catalogs(previous,current,*,today=None):
    """Count changes to *published* IDs and explain entries that disappear.

    Removed IDs can mean an event simply finished yesterday or that a more
    authoritative source now publishes it with a different ID. These are
    not mistaken for cancellations. Remaining removals merit manual review.
    """
    if previous is None:
        return {"available":False,"new":0,"updated":0,"removed":0}
    old=_indexed(previous)
    new=_indexed(current)
    added_ids=new.keys()-old.keys()
    removed_ids=old.keys()-new.keys()
    day=today or dt.datetime.now(ZoneInfo("Atlantic/Canary")).date().isoformat()
    finished=0
    pending=[]
    for key in removed_ids:
        item=old[key]
        until=_day(item.get("end")) or _day(item.get("start"))
        if until and until<day:
            finished+=1
        else:
            pending.append(item)
    replacement_keys=Counter(_identity(new[key]) for key in added_ids)
    replacement_keys.pop(None,None)
    replaced=0
    for item in pending:
        identity=_identity(item)
        if identity and replacement_keys.get(identity,0)>0:
            replaced+=1
            replacement_keys[identity]-=1
    return {
        "available":True,
        "new":len(added_ids),
        "updated":sum(old[key]!=new[key] for key in new.keys() & old.keys()),
        "removed":len(removed_ids),
        "finished":finished,
        "replaced":replaced,
        "review_removed":len(removed_ids)-finished-replaced
    }
