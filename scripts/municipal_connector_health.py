"""Conservative coverage audit for weak Gran Canaria municipal connectors.

Fixed, manually reviewed notices must not be counted as live discovery feeds.
"""
from __future__ import annotations
import datetime as dt

WATCH = {
    "Firgas": ("Firgas · Finaos 2026 contrastados con fuentes locales",),
    "Santa María de Guía": ("Ayuntamientos · actos individualmente contrastados",),
    "Agaete": ("Ayuntamientos · actos individualmente contrastados",),
    "Vega de San Mateo": ("Ayuntamientos · actos individualmente contrastados",),
}

def report(events, results, today):
    sources = {r.get("source"): r for r in results}
    output = {}
    for municipality, curated in WATCH.items():
        upcoming = []
        for event in events:
            if event.get("municipality") != municipality:
                continue
            try:
                last = dt.date.fromisoformat((event.get("end") or event["start"])[:10])
            except (ValueError, TypeError, KeyError):
                continue
            if last >= today:
                upcoming.append(event)
        output[municipality] = {
            "status": "curated_not_live" if upcoming else "no_upcoming_events",
            "live_discovery": False,
            "published_upcoming_cards": len(upcoming),
            "next_event_date": min((e["start"][:10] for e in upcoming), default=None),
            "curated_source_checks_ok": any(
                name in sources and not sources[name].get("error") for name in curated
            ),
            "action_required": True,
            "note": "Verified notices are not a continuously discovering municipal agenda.",
        }
    return output
