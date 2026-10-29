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
    from municipal_live_discovery import PREFIX
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
        live = sources.get(PREFIX + municipality)
        live_ok = live is not None and not live.get("error")
        output[municipality] = {
            "status": ("live_discovery_checked" if live_ok else
                       "live_discovery_failed" if live is not None else
                       "curated_not_live" if upcoming else "no_upcoming_events"),
            "live_discovery": live_ok,
            "live_events_found": live.get("found", 0) if live else 0,
            "live_error": live.get("error", "not configured") if live else "not configured",
            "published_upcoming_cards": len(upcoming),
            "next_event_date": min((e["start"][:10] for e in upcoming), default=None),
            "curated_source_checks_ok": any(
                name in sources and not sources[name].get("error") for name in curated
            ),
            "action_required": not live_ok,
            "note": ("Official listings were scanned; no new event is assumed when no valid event is found." if live_ok else "Official discovery is not operational; curated notices are not a live feed."),
        }
    return output
