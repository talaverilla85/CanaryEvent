"""Apply carefully audited original media to the daily event export.

Each entry must match the same stable SQLite ID, original event title and
source URL. A new event never inherits someone else's image by matching
only an organizer or news index. Do not create stock images.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "official_event_images.json"

ALLOWED_IMAGE_HOSTS = frozenset({
    "auditorioalfredokraus.es", "teatroperezgaldos.es",
    "salainsulardeteatro.com", "teatrocuyas.com",
    "eventos.santabrigida.es", "lpacultura.com",
    "cdn.prod.website-files.com", "tejeda.eu", "valleseco.es",
    "santamariadeguia.es", "api.sociedadfilarmonicalpgc.com",
    "teror.es", "www.galdar.es", "www.maspalomas.com",
    "www.santaluciagc.com", "www.telde.es", "www.arucas.org"
})
DISALLOWED = ("og-image.jpg", "cache_favicon", "favicon",
              "placeholder", "sin-imagen", "img-share", "/logos/", "/icons/")


def validated(record):
    try:
        uri = urlsplit(str(record["image_url"]))
        if (uri.scheme != "https" or uri.hostname not in ALLOWED_IMAGE_HOSTS
                or uri.username or uri.password or len(record["image_url"]) > 700):
            return False
        if any(term in uri.path.lower() for term in DISALLOWED):
            return False
        if not str(record["source_url"]).startswith("https://"):
            return False
        return bool(str(record["title"]).strip() and isinstance(record["id"], int))
    except (KeyError, TypeError, ValueError):
        return False


def apply(events, path=AUDIT):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = raw.get("items", [])
    except (OSError, json.JSONDecodeError):
        return 0
    media = {item["id"]: item for item in records if validated(item)}
    changed = 0
    for e in events:
        m = media.get(e["id"])
        if not m or e.get("image_url") or e["title"] != m["title"] or e["source_url"] != m["source_url"]:
            continue
        for key in ("image_url", "image_alt", "image_origin", "image_status"):
            e[key] = m[key]
        changed += 1
    return changed
