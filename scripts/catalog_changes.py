"""Calculate real public-catalog changes between successful synchronizations.

Source-level 'added'/'changed' counters are *not* proof that an event was
published. Compare the exported public list by its stable event ID instead.
"""
from __future__ import annotations

import json
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


def compare_public_catalogs(previous,current):
    """Unique published IDs added, changed and removed in this *run*.

    An event merely discovered in a source, but held back for review,
    is not counted as newly published.
    """
    if previous is None:
        return {"available":False,"new":0,"updated":0,"removed":0}
    old=_indexed(previous)
    new=_indexed(current)
    return {
        "available":True,
        "new":len(new.keys()-old.keys()),
        "updated":sum(old[key]!=new[key] for key in new.keys() & old.keys()),
        "removed":len(old.keys()-new.keys())
    }
