"""Improve source links ONLY with individually checked official publications.

An override must match the public event's stable ID, title and previous
source_url. URLs from a different event never inherit the override.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "official_event_links.json"
HOSTS = frozenset({"www.galdar.es","teror.es","lpabibliotecas.com"})
CROSS_PUBLISHER_LINKS = frozenset({("www.eventosgrancanaria.com","lpabibliotecas.com")})

def validated(item):
    try:
        old = urlsplit(item["source_url"])
        new = urlsplit(item["verified_url"])
        return (isinstance(item["id"],int)
                and bool(str(item["title"]).strip())
                and old.scheme == new.scheme == "https"
                and (old.hostname == new.hostname or (old.hostname,new.hostname) in CROSS_PUBLISHER_LINKS)
                and new.hostname in HOSTS
                and bool(new.path and new.path != "/")
                and not new.username and not new.password
                and len(item["verified_url"]) < 600)
    except (TypeError,KeyError,ValueError):
        return False

def apply(events, path=AUDIT):
    try:
        items=json.loads(Path(path).read_text(encoding="utf-8")).get("items",[])
    except (OSError,json.JSONDecodeError):
        return 0
    checked={m["id"]:m for m in items if validated(m)}
    changed=0
    for e in events:
        m=checked.get(e["id"])
        if not m or e["title"]!=m["title"] or e["source_url"]!=m["source_url"]:
            continue
        e["source_url"]=m["verified_url"]
        changed+=1
    return changed
