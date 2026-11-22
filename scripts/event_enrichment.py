"""Bounded, evidence-based enrichment for D'Parranda's existing daily sync.

Detect missing material event data, trace the saved source/organizer URLs,
and search for verified event facts in those first-party documents. Reuse
the existing sync's robots-aware HTML fetcher. No scraping in visitors' requests,
no guessed dates, prices, organizer names or AI-written filler.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

SOURCE_HOSTS = frozenset({
    "ingenio.es", "www.ingenio.es", "aguimes.es", "eventos.aguimes.es",
    "actividadesjuventud.laspalmasgc.es", "artesescenicasgrancanaria.com",
    "www.eventosgrancanaria.com", "teatroperezgaldos.es", "auditorioalfredokraus.es",
    "salainsulardeteatro.com", "teatrocuyas.com", "eventos.santabrigida.es",
    "teror.es", "www.galdar.es", "www.arucas.org", "santamariadeguia.es",
    "lpacultura.com", "www.telde.es", "www.santaluciagc.com",
    "www.vegadesanmateo.es", "www.villademoya.es", "www.icdcultural.org",
    "sociedadfilarmonicalpgc.com", "www.tureservaonline.es",
    "www.maspalomas.com", "www.arucas.org",
})
PLACEHOLDERS = re.compile(
    r"^(?:actividad en |actividad publicada|informaci[oó]n b[aá]sica facilitada"
    r"|periodo de actividad|consulta (?:la fuente|los detalles)"
    r"|m[aá]s informaci[oó]n sobre el espect[aá]culo"
    r"|informaci[oó]n del evento|evento publicado|fecha y hora extra[ií]das)", re.I,
)
GENERIC_VENUES = re.compile(
    r"^(?:lugar por confirmar|consultar el recinto|por determinar|varios lugares"
    r"|recinto por confirmar|consultar ubicaci[oó]n)", re.I,
)
ISO_DATE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
ISO_TIME = re.compile(r"^20\d{2}-\d{2}-\d{2}T\d\d:\d\d(?::\d\d)?")

def norm(text):
    value = unicodedata.normalize("NFKD", str(text or "").casefold())
    return re.sub(r"\s+", " ", re.sub(
        r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))
    )).strip()

def meaningful_description(text):
    description = " ".join(str(text or "").split())
    return len(description) >= 125 and not PLACEHOLDERS.match(description)

def gaps(event):
    missing = []
    if not ISO_TIME.match(str(event.get("start") or "")):
        missing.append("hora")
    if not event.get("venue") or GENERIC_VENUES.match(str(event["venue"])):
        missing.append("recinto")
    if not meaningful_description(event.get("details")):
        missing.append("descripcion")
    if event.get("image_status") != "official_remote" or not event.get("image_url"):
        missing.append("cartel")
    if event.get("free") is None and not str(event.get("price") or "").strip():
        missing.append("precio")
    return missing

def trusted_url(value):
    try:
        u = urlsplit(str(value or ""))
        if (u.scheme != "https" or not u.hostname or
            u.hostname not in SOURCE_HOSTS or u.username or u.password or
            u.port not in (None, 443) or u.fragment or len(u.geturl()) > 900):
            return ""
        if not u.path or u.path == "/":
            return ""
        return u.geturl()
    except (ValueError, TypeError):
        return ""

def candidate_sources(event, leads=()):
    # Organizer's linked detail page is more precise than a public listing.
    ordered = [event.get("organizer_url"), event.get("source_url")]
    title = norm(event.get("title"))
    city = norm(event.get("municipality"))
    if len(title) >= 12:
        for lead in leads:
            if not isinstance(lead, dict):
                continue
            if (norm(lead.get("municipality")) != city or
                norm(lead.get("label")) != title):
                continue
            ordered.append(lead.get("url"))
    return list(dict.fromkeys(url for raw in ordered if (url := trusted_url(raw))))

def same_event(event, schema):
    """Require name AND calendar day; a matched title alone is insufficient."""
    title = norm(event.get("title"))
    candidate = norm(schema.get("name"))
    if len(title) < 6 or len(candidate) < 6:
        return False
    if SequenceMatcher(None, title, candidate).ratio() < 0.83:
        return False
    start = str(schema.get("startDate") or "")
    return start[:10] == str(event.get("start") or "")[:10] and bool(ISO_DATE.fullmatch(start[:10]))

def schema_nodes(soup):
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            root = json.loads(tag.string or tag.get_text())
        except (ValueError, TypeError):
            continue
        nodes = root if isinstance(root, list) else [root]
        todo = list(nodes)
        while todo:
            node = todo.pop(0)
            if isinstance(node, list):
                todo.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            kinds = node.get("@type", [])
            kinds = [kinds] if isinstance(kinds, str) else kinds
            if any(str(k).split("/")[-1] == "Event" for k in kinds):
                yield node
            graph = node.get("@graph")
            if isinstance(graph, (dict, list)):
                todo.append(graph)

def structured_evidence(event, soup):
    for schema in schema_nodes(soup):
        if not same_event(event, schema):
            continue
        changes = {}
        data = schema.get("description", "")
        if isinstance(data, str):
            description = " ".join(BeautifulSoup(data, "html.parser").stripped_strings)
            if (not meaningful_description(event.get("details")) and
                meaningful_description(description)):
                # A concise original description, never a full scraped article.
                changes["details"] = description[:260].rsplit(" ", 1)[0]
        # A date-only listing can safely inherit the verified published clock.
        start = str(schema.get("startDate") or "")
        if "hora" in gaps(event) and ISO_TIME.match(start):
            changes["start"] = start[:19] if len(start) >= 19 else start[:16] + ":00"
        loc = schema.get("location")
        if "recinto" in gaps(event) and isinstance(loc, dict):
            venue = loc.get("name")
            if isinstance(venue, str) and 7 <= len(venue.strip()) <= 110:
                if norm(venue) != norm(event.get("municipality")):
                    changes["venue"] = venue.strip()
        return changes
    return {}

def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS event_enrichment_checks (
      event_id INTEGER PRIMARY KEY,
      checked_at TEXT NOT NULL,
      original_source TEXT NOT NULL,
      evidence_url TEXT NOT NULL DEFAULT '',
      missing_before TEXT NOT NULL,
      missing_after TEXT NOT NULL,
      verified_changes TEXT NOT NULL DEFAULT '{}',
      outcome TEXT NOT NULL DEFAULT ''
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS event_enrichment_proofs (
      event_id INTEGER NOT NULL,
      field_name TEXT NOT NULL,
      verified_value TEXT NOT NULL,
      original_source TEXT NOT NULL,
      evidence_url TEXT NOT NULL,
      verified_at TEXT NOT NULL,
      PRIMARY KEY(event_id,field_name)
    )""")

def load_radar_leads(path):
    path = Path(path)
    if not path.is_file():
        return ()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return tuple(doc.get("leads") or ())
    except (ValueError, OSError, TypeError):
        return ()

def enrich(conn, now, today, *, fetch_html, leads=(), max_requests=8, cooldown_hours=72):
    """Record proof for every attempted fix; only change independently matched facts.

    The crawler is injected by sync_events.get_html and already checks robots.txt
    and caps source response sizes. Cap total HTTP fetches across ALL sources.
    """
    init(conn)
    if not callable(fetch_html):
        raise ValueError("A robots-aware fetch_html function is required")
    today_text = today.isoformat() if hasattr(today, "isoformat") else str(today)
    now_iso = str(now)
    rows = [dict(r) for r in conn.execute(
        """SELECT * FROM events WHERE status='approved'
           AND substr(COALESCE("end",start),1,10) >= ?
           ORDER BY start ASC LIMIT 3500""", (today_text,)
    )]
    # Cache fetch results in a run; multiple sessions can share one source page.
    html_cache = {}
    inspected = changed = requests = skipped = 0
    outcomes = {"verified": 0, "no_matching_evidence": 0, "source_failed": 0, "no_eligible_source": 0}
    gap_counts = {field: 0 for field in ("hora", "recinto", "descripcion", "cartel", "precio")}
    for row in rows:
        for field in gaps(row):
            gap_counts[field] += 1
    for e in rows:
        before = gaps(e)
        if not any(field in before for field in ("descripcion", "recinto", "hora")):
            continue
        previous = conn.execute(
            "SELECT checked_at FROM event_enrichment_checks WHERE event_id=?",
            (e["id"],)
        ).fetchone()
        if previous:
            try:
                checked_at = dt.datetime.fromisoformat(previous[0])
                if dt.datetime.fromisoformat(now_iso) - checked_at < dt.timedelta(hours=cooldown_hours):
                    skipped += 1
                    continue
            except (ValueError, TypeError):
                pass
        if requests >= max_requests:
            break
        inspected += 1
        sources = candidate_sources(e, leads)
        change = {}
        proof = ""
        outcome = "no_eligible_source" if not sources else "no_matching_evidence"
        for url in sources:
            if url not in html_cache:
                if requests >= max_requests:
                    break
                requests += 1
                try:
                    html_cache[url] = fetch_html(url)
                except Exception:
                    html_cache[url] = None
            soup = html_cache[url]
            if soup is None:
                outcome = "source_failed"
                continue
            proposal = structured_evidence(e, soup)
            # Don't overwrite valuable fields and don't infer values.
            if proposal:
                change = proposal
                proof = url
                outcome = "verified"
                break
        if change:
            permitted = {"details", "venue", "start"}
            for field, value in change.items():
                if field not in permitted:
                    raise ValueError("Unexpected enrichment field")
                conn.execute("UPDATE events SET "+field+"=?,updated_at=? WHERE id=?",
                             (value, now_iso, e["id"]))
                conn.execute("""INSERT INTO event_enrichment_proofs
                    (event_id,field_name,verified_value,original_source,evidence_url,verified_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(event_id,field_name) DO UPDATE SET
                      verified_value=excluded.verified_value,
                      original_source=excluded.original_source,
                      evidence_url=excluded.evidence_url,
                      verified_at=excluded.verified_at""",
                    (e["id"], field, str(value), str(e.get("source_url") or ""), proof, now_iso))
                e[field] = value
            changed += 1
        outcomes[outcome] += 1
        conn.execute(
            """INSERT INTO event_enrichment_checks
               (event_id,checked_at,original_source,evidence_url,missing_before,
                missing_after,verified_changes,outcome) VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(event_id) DO UPDATE SET
                 checked_at=excluded.checked_at,original_source=excluded.original_source,
                 evidence_url=excluded.evidence_url,missing_before=excluded.missing_before,
                 missing_after=excluded.missing_after,
                 verified_changes=excluded.verified_changes,outcome=excluded.outcome""",
            (e["id"], now_iso, str(e.get("source_url") or ""),
             proof, json.dumps(before), json.dumps(gaps(e)), json.dumps(change, ensure_ascii=False), outcome)
        )
        conn.commit()
        if requests >= max_requests:
            break
    return {
        "active_events": len(rows), "checked": inspected, "verified": changed,
        "requests": requests, "cooldown_skipped": skipped,
        "missing_by_field": gap_counts, "outcomes": outcomes
    }
