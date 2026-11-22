"""Conservative daily SEO enrichment, after all original source-specific extractors.

A persistent SQLite queue revisits incomplete upcoming events over successive
runs. Only a precisely matched Event on an approved official source can add
facts. All fetching uses sync_events.get_html (robots-aware and size-bounded);
no network calls occur while visitors open an SEO page.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

import verified_venue_coordinates
import venue_quality

SOURCE_HOSTS = frozenset({
    "ingenio.es", "www.ingenio.es", "aguimes.es", "eventos.aguimes.es",
    "actividadesjuventud.laspalmasgc.es", "artesescenicasgrancanaria.com",
    "www.artesescenicasgrancanaria.com", "www.eventosgrancanaria.com",
    "teatroperezgaldos.es", "auditorioalfredokraus.es",
    "salainsulardeteatro.com", "teatrocuyas.com", "eventos.santabrigida.es",
    "teror.es", "www.galdar.es", "www.arucas.org", "santamariadeguia.es",
    "lpacultura.com", "www.telde.es", "www.santaluciagc.com",
    "www.vegadesanmateo.es", "vegadesanmateo.es",
    "www.villademoya.es", "www.icdcultural.org", "cultura.icdcultural.org",
    "sociedadfilarmonicalpgc.com", "www.tureservaonline.es",
    "www.maspalomas.com", "tejeda.eu", "valleseco.es",
    "lpabibliotecas.com", "www.lpabibliotecas.com",
    "casafrica.es", "www.casafrica.es", "ofgrancanaria.com",
})
# In lockstep with lib/seo-pages.js: an image outside this list is never
# promoted to official_remote from automatic metadata.
IMAGE_HOSTS = frozenset({
    "ingenio.es", "www.ingenio.es", "eventos.aguimes.es",
    "actividadesjuventud.laspalmasgc.es", "artesescenicasgrancanaria.com",
    "www.artesescenicasgrancanaria.com", "www.eventosgrancanaria.com",
    "www.tureservaonline.es", "auditorioalfredokraus.es",
    "teatroperezgaldos.es", "salainsulardeteatro.com", "teatrocuyas.com",
    "eventos.santabrigida.es", "lpacultura.com", "cdn.prod.website-files.com",
    "tejeda.eu", "valleseco.es", "santamariadeguia.es",
    "api.sociedadfilarmonicalpgc.com", "teror.es", "www.galdar.es",
    "www.arucas.org", "lpabibliotecas.com", "www.maspalomas.com",
    "www.santaluciagc.com", "www.telde.es",
})
PLACEHOLDERS = re.compile(
    r"^(?:actividad en |actividad publicada|informaci[oó]n b[aá]sica facilitada"
    r"|periodo de actividad|consulta (?:la fuente|los detalles)"
    r"|m[aá]s informaci[oó]n sobre el espect[aá]culo"
    r"|informaci[oó]n del evento|evento publicado|fecha y hora extra[ií]das)", re.I,
)
DATE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
DATE_TIME = re.compile(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")
MAX_EVENTS_PER_RUN = 40
SEO_DESCRIPTION_MIN = 145
CANARY_TZ = ZoneInfo("Atlantic/Canary")
MAIN_GAPS = frozenset(("hora", "recinto", "ubicacion", "descripcion", "cartel", "precio"))


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return re.sub(r"\s+", " ", re.sub(
        r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))
    )).strip()


def meaningful_description(value):
    text = " ".join(str(value or "").split())
    return len(text) >= SEO_DESCRIPTION_MIN and not PLACEHOLDERS.match(text)


def gaps(event):
    """Quality gaps are specific; missing price/poster aren't SEO hard blockers."""
    missing = []
    if not DATE_TIME.fullmatch(str(event.get("start") or "")):
        missing.append("hora")
    if not venue_quality.named_venue(event):
        missing.append("recinto")
    elif event.get("accuracy") != "venue":
        missing.append("ubicacion")
    if not meaningful_description(event.get("details")):
        missing.append("descripcion")
    if event.get("image_status") != "official_remote" or not event.get("image_url"):
        missing.append("cartel")
    if event.get("free") is None and not str(event.get("price") or "").strip():
        missing.append("precio")
    return missing


def seo_ready(event):
    """Mirrors lib/event-seo.js; skip external price or poster requirements."""
    return bool(
        int(event.get("id") or 0) > 0
        and len(str(event.get("title") or "").strip()) >= 5
        and str(event.get("municipality") or "").strip()
        and venue_quality.named_venue(event)
        and event.get("accuracy") == "venue"
        and DATE_TIME.fullmatch(str(event.get("start") or ""))
        and meaningful_description(event.get("details"))
        and str(event.get("source_url") or "").startswith("https://")
    )


def trusted_url(value):
    try:
        url = urlsplit(str(value or ""))
        if (url.scheme != "https" or url.hostname not in SOURCE_HOSTS
                or url.username or url.password or url.port not in (None, 443)
                or url.fragment or len(url.geturl()) > 900
                or not url.path or url.path == "/"):
            return ""
        return url.geturl()
    except (ValueError, TypeError):
        return ""


def official_image_url(value):
    try:
        url = urlsplit(str(value or ""))
        if (url.scheme != "https" or url.hostname not in IMAGE_HOSTS
                or url.username or url.password or url.port not in (None, 443)
                or len(url.geturl()) > 900 or url.fragment):
            return ""
        return url.geturl()
    except (ValueError, TypeError):
        return ""


def candidate_sources(event, leads=()):
    original = [event.get("organizer_url"), event.get("source_url")]
    title, city = norm(event.get("title")), norm(event.get("municipality"))
    if len(title) >= 12:
        for lead in leads:
            if not isinstance(lead, dict):
                continue
            if (norm(lead.get("municipality")) == city
                    and norm(lead.get("label")) == title
                    and lead.get("publication_status") != "not_an_event"):
                original.append(lead.get("url"))
    return list(dict.fromkeys(url for raw in original if (url := trusted_url(raw))))


def candidate_detail_links(soup, event, base_url):
    """From an official listing, follow only exact-title official detail links."""
    result = []
    event_name = norm(event.get("title"))
    if len(event_name) < 10:
        return result
    for anchor in soup.select("a[href]")[:400]:
        label = norm(anchor.get_text(" ", strip=True))
        if not label or SequenceMatcher(None, label, event_name).ratio() < .93:
            continue
        url = trusted_url(urljoin(base_url, anchor.get("href", "")))
        if url and url != base_url and urlsplit(url).hostname == urlsplit(base_url).hostname:
            if url not in result:
                result.append(url)
        if len(result) == 2:
            break
    return result


def same_event(event, schema):
    title, candidate = norm(event.get("title")), norm(schema.get("name"))
    if len(title) < 6 or len(candidate) < 6:
        return False
    if SequenceMatcher(None, title, candidate).ratio() < .83:
        return False
    stamp = str(schema.get("startDate") or "")
    if stamp[:10] != str(event.get("start") or "")[:10] or not DATE.fullmatch(stamp[:10]):
        return False
    location = schema.get("location")
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            locality = address.get("addressLocality")
            if locality and norm(locality) != norm(event.get("municipality")):
                return False
    return True


def schema_nodes(soup):
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            node = json.loads(tag.string or tag.get_text())
        except (ValueError, TypeError):
            continue
        stack = list(node) if isinstance(node, list) else [node]
        while stack:
            entry = stack.pop()
            if isinstance(entry, list):
                stack.extend(entry)
            elif isinstance(entry, dict):
                kinds = entry.get("@type", [])
                kinds = [kinds] if isinstance(kinds, str) else kinds
                if any(str(k).split("/")[-1] == "Event" for k in kinds):
                    yield entry
                graph = entry.get("@graph")
                if isinstance(graph, (dict, list)):
                    stack.append(graph)


def canary_start(value):
    """Convert aware official timestamps to island local clock, not string-slice UTC."""
    value = str(value or "")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d\d:\d\d(?::\d\d)?(?:Z|[+-]\d\d:\d\d)?", value):
        return ""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(CANARY_TZ)
        return parsed.replace(tzinfo=None).isoformat(timespec="seconds")
    except ValueError:
        return ""


def verified_geo(location, municipality):
    """Accept published event-specific coordinates only with matching locality."""
    if not isinstance(location, dict) or not isinstance(location.get("geo"), dict):
        return None
    address = location.get("address")
    if not isinstance(address, dict) or norm(address.get("addressLocality")) != norm(municipality):
        return None
    geo = location["geo"]
    try:
        lat, lng = float(geo["latitude"]), float(geo["longitude"])
    except (KeyError, ValueError, TypeError):
        return None
    if not (27.65 <= lat <= 28.30 and -16.05 <= lng <= -15.25):
        return None
    return lat, lng


def verified_offer(offers):
    """Only a single explicit EUR price; never infer a free event from silence."""
    if isinstance(offers, list):
        if len(offers) != 1:
            return None
        offers = offers[0]
    if not isinstance(offers, dict) or str(offers.get("priceCurrency") or "").upper() != "EUR":
        return None
    if isinstance(offers.get("price"), bool):
        return None
    try:
        value = float(offers["price"])
    except (KeyError, ValueError, TypeError):
        return None
    if not (0 <= value <= 10000):
        return None
    if value == 0:
        return {"free": 1, "price": "Gratis"}
    return {"free": 0, "price": (f"{value:g}".replace(".", ",") + " €")}


def structured_evidence(event, soup):
    """Use one unambiguous title+day matched official Event JSON-LD node."""
    matching = [node for node in schema_nodes(soup) if same_event(event, node)]
    if len(matching) != 1:
        return {}
    schema = matching[0]
    changes = {}
    data = schema.get("description", "")
    if isinstance(data, str) and "descripcion" in gaps(event):
        text = " ".join(BeautifulSoup(data, "html.parser").stripped_strings)
        if meaningful_description(text):
            changes["details"] = text[:450].rsplit(" ", 1)[0] if len(text) > 450 else text
    start = canary_start(schema.get("startDate"))
    if "hora" in gaps(event) and DATE_TIME.fullmatch(start) and start[:10] == str(event.get("start") or "")[:10]:
        changes["start"] = start
    location = schema.get("location")
    if isinstance(location, dict):
        name = location.get("name")
        if isinstance(name, str) and 7 <= len(name.strip()) <= 110:
            venue = name.strip()
            if venue_quality.named_venue({"venue": venue, "municipality": event.get("municipality")}):
                if "recinto" in gaps(event):
                    changes["venue"] = venue
                if norm(venue) == norm(changes.get("venue") or event.get("venue")):
                    geo = verified_geo(location, event.get("municipality"))
                    if not geo:
                        stored = verified_venue_coordinates.find(event.get("municipality"), venue)
                        geo = (stored[0], stored[1]) if stored else None
                    if geo and event.get("accuracy") != "venue":
                        changes.update(lat=geo[0], lng=geo[1], accuracy="venue")
                        changes["_geo_proof"] = json.dumps({
                            "venue": venue, "municipality": event.get("municipality"),
                            "title": norm(event.get("title")),
                            "day": str(event.get("start") or "")[:10],
                            "lat": geo[0], "lng": geo[1],
                        }, ensure_ascii=False, sort_keys=True)
    if "precio" in gaps(event):
        price = verified_offer(schema.get("offers"))
        if price:
            changes.update(price)
    if "cartel" in gaps(event):
        item = schema.get("image")
        if isinstance(item, list):
            item = item[0] if len(item) == 1 else None
        if isinstance(item, dict):
            item = item.get("url") or item.get("contentUrl")
        url = official_image_url(item)
        if url:
            changes["image_url"] = url
            changes["image_status"] = "official_remote"
    return changes


def verified_page_evidence(event, soup):
    """Fallback for an official event detail page without Event JSON-LD.

    An exact event H1 and one unambiguous <time datetime> on the event day
    must be present. Never read a generic agenda listing or unrelated post.
    Only a source-authored meta description/time can be copied here.
    """
    if any(schema_nodes(soup)):
        return {}  # Conflicting Event metadata must never be bypassed.
    title = norm(event.get("title"))
    headings = [norm(h.get_text(" ", strip=True)) for h in soup.select("h1")]
    if len([h for h in headings if h == title]) != 1:
        return {}
    times = {str(tag.get("datetime") or "") for tag in soup.select("time[datetime]")}
    times = {t for t in times if DATE.fullmatch(t[:10])}
    if len(times) != 1:
        return {}
    stamp = next(iter(times))
    if stamp[:10] != str(event.get("start") or "")[:10]:
        return {}
    result = {}
    if "descripcion" in gaps(event):
        for sel in ('meta[property="og:description"]', 'meta[name="description"]'):
            tag = soup.select_one(sel)
            text = " ".join(str(tag.get("content") or "").split()) if tag else ""
            if meaningful_description(text):
                result["details"] = text[:450].rsplit(" ", 1)[0] if len(text) > 450 else text
                break
    if "hora" in gaps(event):
        clock = canary_start(stamp)
        if DATE_TIME.fullmatch(clock) and clock[:10] == stamp[:10]:
            result["start"] = clock
    return result


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
    fields = {row[1] for row in conn.execute("PRAGMA table_info(event_enrichment_checks)")}
    if "attempts" not in fields:
        conn.execute("ALTER TABLE event_enrichment_checks ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
    if "next_check_at" not in fields:
        conn.execute("ALTER TABLE event_enrichment_checks ADD COLUMN next_check_at TEXT NOT NULL DEFAULT ''")
    conn.execute("""CREATE TABLE IF NOT EXISTS event_enrichment_proofs (
      event_id INTEGER NOT NULL,
      field_name TEXT NOT NULL,
      verified_value TEXT NOT NULL,
      original_source TEXT NOT NULL,
      evidence_url TEXT NOT NULL,
      verified_at TEXT NOT NULL,
      PRIMARY KEY(event_id,field_name)
    )""")
    # Prevent a subsequent source refresh from erasing verified improvements.
    # Old proofs without an identity record are never blindly replayed.
    conn.execute("""CREATE TABLE IF NOT EXISTS event_enrichment_identity (
      event_id INTEGER PRIMARY KEY, title_key TEXT NOT NULL,
      date_key TEXT NOT NULL, original_source TEXT NOT NULL
    )""")


def restore_verified(conn, rows, now):
    identities = {r[0]: r[1:] for r in conn.execute(
        "SELECT event_id,title_key,date_key,original_source FROM event_enrichment_identity")}
    proofs = {}
    for event_id, field, value in conn.execute(
        "SELECT event_id,field_name,verified_value FROM event_enrichment_proofs"):
        proofs.setdefault(event_id, {})[field] = value
    restored = 0
    for e in rows:
        identity = identities.get(e["id"])
        if not identity or identity != (
            norm(e.get("title")), str(e.get("start") or "")[:10],
            str(e.get("source_url") or "")):
            continue
        saved = proofs.get(e["id"], {})
        before = gaps(e)
        changes = {}
        if "descripcion" in before and meaningful_description(saved.get("details")):
            changes["details"] = saved["details"]
        if "hora" in before and DATE_TIME.fullmatch(saved.get("start", "")):
            if saved["start"][:10] == str(e.get("start") or "")[:10]:
                changes["start"] = saved["start"]
        if "recinto" in before:
            venue = saved.get("venue", "")
            if venue_quality.named_venue({"venue": venue, "municipality": e.get("municipality")}):
                changes["venue"] = venue
        if "cartel" in before and official_image_url(saved.get("image_url")):
            if saved.get("image_status") == "official_remote":
                changes.update(image_url=saved["image_url"], image_status="official_remote")
        if "precio" in before and saved.get("free") in ("0", "1") and saved.get("price"):
            changes.update(price=saved["price"], free=int(saved["free"]))
        if ("ubicacion" in before or "recinto" in before) and saved.get("geo"):
            try:
                geo = json.loads(saved["geo"])
                lat, lng = float(geo["lat"]), float(geo["lng"])
                if (norm(geo.get("venue")) == norm(changes.get("venue") or e.get("venue"))
                        and norm(geo.get("municipality")) == norm(e.get("municipality"))
                        and geo.get("day") == str(e.get("start") or "")[:10]
                        and 27.65 <= lat <= 28.30 and -16.05 <= lng <= -15.25):
                    changes.update(lat=lat, lng=lng, accuracy="venue")
            except (TypeError, ValueError, KeyError):
                pass
        for field, value in changes.items():
            conn.execute("UPDATE events SET " + field + "=?,updated_at=? WHERE id=?",
                         (value, str(now), e["id"]))
            e[field] = value
        restored += bool(changes)
    if restored:
        conn.commit()
    return restored


def load_radar_leads(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        return tuple(doc.get("leads") or ())
    except (OSError, ValueError, TypeError):
        return ()


def retry_at(now, outcome, attempts, still_missing):
    if not still_missing:
        return ""
    # Recover quickly from transient failures; avoid hammering unchanged pages.
    base_days = {"verified": 1, "source_failed": 1, "no_matching_evidence": 3,
                 "no_eligible_source": 7}.get(outcome, 3)
    days = min(14, base_days * (2 ** min(max(attempts - 1, 0), 3)))
    return (now + dt.timedelta(days=days)).isoformat()


def enrich(conn, now, today, *, fetch_html, leads=(), max_requests=16,
           cooldown_hours=72, max_events=MAX_EVENTS_PER_RUN):
    """Incrementally drain the pending queue with bounded, robots-aware visits.

    Persist the next check and evidence in the existing tracked SQLite file.
    Event identity, source-specific parsing, and existing complete fields remain.
    """
    init(conn)
    if not callable(fetch_html):
        raise ValueError("A robots-aware fetch_html function is required")
    now_dt = dt.datetime.fromisoformat(str(now))
    today_text = today.isoformat() if hasattr(today, "isoformat") else str(today)
    rows = [dict(row) for row in conn.execute(
        """SELECT * FROM events WHERE status='approved'
           AND substr(COALESCE("end",start),1,10) >= ?
           ORDER BY start ASC LIMIT 3500""", (today_text,)
    )]
    restored = restore_verified(conn, rows, now)
    previous = {row["event_id"]: dict(row) for row in conn.execute(
        "SELECT * FROM event_enrichment_checks")}
    gap_counts = {name: 0 for name in ("hora", "recinto", "ubicacion", "descripcion", "cartel", "precio")}
    pending = []
    skipped = 0
    for e in rows:
        missing = gaps(e)
        for name in missing:
            gap_counts[name] += 1
        if not missing:
            continue
        prev = previous.get(e["id"])
        # A newly changed source record goes back to the queue immediately.
        unchanged = (prev and prev["missing_after"] == json.dumps(missing, ensure_ascii=False)
                     and prev["original_source"] == str(e.get("source_url") or ""))
        next_due = str(prev.get("next_check_at") or "") if unchanged else ""
        if next_due:
            try:
                if dt.datetime.fromisoformat(next_due) > now_dt:
                    skipped += 1
                    continue
            except ValueError:
                pass
        elif unchanged and prev:
            # Backward compatibility with the existing first-generation checks.
            try:
                last = dt.datetime.fromisoformat(prev["checked_at"])
                if now_dt - last < dt.timedelta(hours=cooldown_hours):
                    skipped += 1
                    continue
            except (TypeError, ValueError):
                pass
        pending.append((e, missing, prev if unchanged else None))
    # First work on unvisited events, then due rechecks; among each group,
    # give priority to upcoming sessions and items blocking SEO indexing.
    pending.sort(key=lambda item: (
        1 if item[2] else 0,
        1 if seo_ready(item[0]) else 0,
        (item[0].get("end") or item[0].get("start") or "9999")[:10],
        -sum(name in item[1] for name in ("hora", "recinto", "ubicacion", "descripcion")),
        item[0]["id"],
    ))
    cache = {}
    requests = checked = verified = newly_eligible = 0
    outcomes = {"verified": 0, "no_matching_evidence": 0,
                "source_failed": 0, "no_eligible_source": 0}
    for e, before, prev in pending:
        if checked >= max_events or requests >= max_requests:
            break
        checked += 1
        ready_before = seo_ready(e)
        sources = candidate_sources(e, leads)
        outcome = "no_eligible_source" if not sources else "no_matching_evidence"
        change, proof = {}, ""
        # Only one level of matching official detail links; never spider the web.
        to_visit = list(sources)
        seen = set()
        while to_visit and requests < max_requests and not change:
            url = to_visit.pop(0)
            if url in seen:
                continue
            seen.add(url)
            if url not in cache:
                requests += 1
                try:
                    cache[url] = fetch_html(url)
                except Exception:
                    cache[url] = None
            soup = cache[url]
            if soup is None:
                outcome = "source_failed"
                continue
            change = structured_evidence(e, soup) or verified_page_evidence(e, soup)
            if change:
                proof, outcome = url, "verified"
                break
            for link in candidate_detail_links(soup, e, url):
                if link not in seen and link not in to_visit:
                    to_visit.append(link)
        if change:
            allowed = {"details", "venue", "start", "lat", "lng", "accuracy",
                       "price", "free", "image_url", "image_status"}
            geo_proof = change.pop("_geo_proof", None)
            for field, value in change.items():
                if field not in allowed:
                    raise ValueError("Unexpected enrichment field")
                conn.execute("UPDATE events SET " + field + "=?,updated_at=? WHERE id=?",
                             (value, str(now), e["id"]))
                conn.execute("""INSERT INTO event_enrichment_proofs
                    (event_id,field_name,verified_value,original_source,evidence_url,verified_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(event_id,field_name) DO UPDATE SET
                      verified_value=excluded.verified_value,
                      original_source=excluded.original_source,
                      evidence_url=excluded.evidence_url,
                      verified_at=excluded.verified_at""",
                    (e["id"], field, str(value), str(e.get("source_url") or ""), proof, str(now)))
                e[field] = value
            conn.execute("""INSERT INTO event_enrichment_identity
                (event_id,title_key,date_key,original_source) VALUES(?,?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET
                title_key=excluded.title_key,date_key=excluded.date_key,
                original_source=excluded.original_source""",
                (e["id"], norm(e.get("title")), str(e.get("start") or "")[:10],
                 str(e.get("source_url") or "")))
            if geo_proof:
                conn.execute("""INSERT INTO event_enrichment_proofs
                    (event_id,field_name,verified_value,original_source,evidence_url,verified_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(event_id,field_name) DO UPDATE SET
                      verified_value=excluded.verified_value,
                      original_source=excluded.original_source,
                      evidence_url=excluded.evidence_url,
                      verified_at=excluded.verified_at""",
                    (e["id"], "geo", geo_proof, str(e.get("source_url") or ""), proof, str(now)))
            verified += 1
        after = gaps(e)
        if not ready_before and seo_ready(e):
            newly_eligible += 1
        attempts = 1 + (int(prev.get("attempts") or 0) if prev else 0)
        next_due = retry_at(now_dt, outcome, attempts, after)
        outcomes[outcome] += 1
        conn.execute("""INSERT INTO event_enrichment_checks
              (event_id,checked_at,original_source,evidence_url,missing_before,
               missing_after,verified_changes,outcome,attempts,next_check_at)
              VALUES(?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(event_id) DO UPDATE SET
              checked_at=excluded.checked_at,original_source=excluded.original_source,
              evidence_url=excluded.evidence_url,missing_before=excluded.missing_before,
              missing_after=excluded.missing_after,verified_changes=excluded.verified_changes,
              outcome=excluded.outcome,attempts=excluded.attempts,
              next_check_at=excluded.next_check_at""",
            (e["id"], str(now), str(e.get("source_url") or ""), proof,
             json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False),
             json.dumps(change, ensure_ascii=False), outcome, attempts, next_due))
        conn.commit()
    return {
        "active_events": len(rows), "pending": len(pending), "checked": checked,
        "verified": verified, "restored": restored, "newly_eligible": newly_eligible,
        "requests": requests, "cooldown_skipped": skipped,
        "missing_by_field": gap_counts, "outcomes": outcomes,
    }
