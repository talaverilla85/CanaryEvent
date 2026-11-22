"""D'Parranda SEO weekly digest and low-noise Telegram health monitor.

The weekly counters come from the LIVE public sitemap and catalog, not from
guessing Google indexing. Weekly verified improvements come from the
versioned SQLite evidence table. A compact snapshot in Git provides a baseline.
The same existing Telegram bot credentials are used; no user data is sent.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from telegram_health_alert import send

ROOT = Path(__file__).resolve().parents[1]
SITEMAP_URL = "https://dparranda.es/sitemap-eventos.xml"
CATALOG_URL = "https://dparranda.es/api/catalog"
WEEKLY_STATE = ROOT / "data" / "seo_weekly_snapshot.json"
MONITOR_STATE = ROOT / "data" / "seo_monitor_state.json"
ENRICHMENT_STATUS = ROOT / "data" / "seo_enrichment_status.json"
SQLITE_FILE = ROOT / "data" / "events.sqlite"
URL_ID = re.compile(r"^https://dparranda\.es/evento/([1-9][0-9]*)$")
XML_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_STALE_HOURS = 72


def read_json(path, default=None):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default if default is not None else {})
    except (OSError, ValueError, TypeError):
        return default if default is not None else {}


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def utc(value):
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(dt.timezone.utc)


def week_ending(now):
    """Previous/current Sunday, so a manually delayed run never invents next week's results."""
    day = utc(now).date()
    return (day - dt.timedelta(days=(day.weekday() + 1) % 7)).isoformat()


def get_sitemap(*, session=requests):
    response = session.get(SITEMAP_URL, timeout=18, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError("Sitemap unavailable")
    if "xml" not in response.headers.get("content-type", "").lower():
        raise ValueError("Sitemap is not XML")
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as error:
        raise ValueError("Invalid sitemap XML") from error
    if root.tag != XML_NAMESPACE + "urlset":
        raise ValueError("Unexpected sitemap format")
    urls = [node.text for node in root.findall(f"{XML_NAMESPACE}url/{XML_NAMESPACE}loc")]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicated sitemap URLs")
    ids = []
    for url in urls:
        match = URL_ID.fullmatch(url or "")
        if not match:
            raise ValueError("Unexpected sitemap URL")
        ids.append(int(match[1]))
    return set(ids)


def get_catalog(*, session=requests):
    response = session.get(CATALOG_URL, timeout=18, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError("Catalog unavailable")
    document = response.json()
    if not isinstance(document, dict) or not isinstance(document.get("events"), list):
        raise ValueError("Invalid catalog format")
    # No sponsored events or generated negative-ID sessions in the SEO backlog.
    result = set()
    for event in document["events"]:
        if not isinstance(event, dict):
            continue
        identifier = event.get("id")
        if type(identifier) is int and identifier > 0 and not event.get("paid_promotion"):
            result.add(identifier)
    return result


def verified_last_week(path, since, active_ids):
    """Distinct active event IDs with a verified enrichment proof in the last 7d."""
    if not Path(path).is_file():
        return 0
    try:
        with closing(sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
            if not conn.execute("""SELECT 1 FROM sqlite_master
                                   WHERE type='table' AND name='event_enrichment_proofs'""").fetchone():
                return 0
            rows = conn.execute("SELECT event_id, verified_at FROM event_enrichment_proofs").fetchall()
    except sqlite3.Error:
        return 0
    recent = set()
    for event_id, when in rows:
        try:
            if int(event_id) in active_ids and utc(when) >= since:
                recent.add(int(event_id))
        except (ValueError, TypeError, OverflowError):
            continue
    return len(recent)


def weekly_data(now, eligible_ids, active_ids, previous, improved):
    now = utc(now)
    week = week_ending(now)
    old_ids = previous.get("eligible_ids")
    baseline = isinstance(old_ids, list) and previous.get("week_ending") != week and all(
        type(x) is int and x > 0 for x in old_ids
    )
    old = set(old_ids) if baseline else set()
    return {
        "schema_version": 1,
        "week_ending": week,
        "checked_at": now.isoformat(),
        "eligible_ids": sorted(eligible_ids),
        "active_candidates": len(active_ids),
        "pending_candidates": len(active_ids - eligible_ids),
        "verified_events_last_7d": improved,
        "previous_eligible_count": len(old) if baseline else None,
        "newly_eligible": len(eligible_ids - old) if baseline else None,
        "no_longer_eligible": len(old - eligible_ids) if baseline else None,
    }


def make_weekly_message(snapshot, *, previous=None):
    count = len(snapshot["eligible_ids"])
    prior = snapshot["previous_eligible_count"]
    delta = "primera medición" if prior is None else f"{prior} → {count}"
    new = "Sin medición anterior" if prior is None else str(snapshot["newly_eligible"])
    lost = "" if prior is None or not snapshot["no_longer_eligible"] else (
        "\n📅 Fichas que dejaron de ser aptas: " + str(snapshot["no_longer_eligible"])
        + " (por caducidad o cambios)"
    )
    return (
        "📈 DParranda · Informe SEO semanal\n"
        "Semana terminada el " + snapshot["week_ending"][8:10] + "/"
        + snapshot["week_ending"][5:7] + "/" + snapshot["week_ending"][:4] + "\n\n"
        "📄 Fichas aptas para Google: " + str(count) + " (" + delta + ")\n"
        "🆕 Nuevas fichas aptas: " + new + "\n"
        "🛠 Eventos con datos mejorados y verificados (7 días): "
        + str(snapshot["verified_events_last_7d"]) + "\n"
        "⏳ Eventos vigentes aún pendientes del filtro: "
        + str(snapshot["pending_candidates"]) + " de "
        + str(snapshot["active_candidates"]) + " candidatos"
        + lost + "\n\n"
        "🔎 Son fichas aptas para indexación; no equivalen a páginas ya indexadas por Google.\n"
        "Sitemap: " + SITEMAP_URL
    )


def enrichment_stale(now, status):
    try:
        checked = utc(status["checked_at"])
        age = utc(now) - checked
        return age > dt.timedelta(hours=MAX_STALE_HOURS) or age < -dt.timedelta(hours=2)
    except (ValueError, KeyError, TypeError, OverflowError):
        return True


def monitor_result(now, status, sitemap_ok, previous):
    """Two consecutive failed DAILY checks for sitemap; 72h of stale enrichment.

    State changes only when necessary. After an alert, suppress repeats until
    recovery. A single connection hiccup is silently retried the next day.
    """
    old = previous if isinstance(previous, dict) else {}
    sitemap_failures = int(old.get("sitemap_failures", 0)) if type(old.get("sitemap_failures", 0)) is int else 0
    sitemap_alerted = old.get("sitemap_alerted") is True
    enrichment_alerted = old.get("enrichment_alerted") is True
    stale = enrichment_stale(now, status)
    failures = 0 if sitemap_ok else min(3, sitemap_failures + 1)
    alert_parts, recovery_parts = [], []
    if failures >= 2 and not sitemap_alerted:
        alert_parts.append("El sitemap de eventos ha fallado en dos comprobaciones diarias.")
    if stale and not enrichment_alerted:
        alert_parts.append("El informe de enriquecimiento no se actualiza desde hace más de 72 horas.")
    if sitemap_ok and sitemap_alerted:
        recovery_parts.append("sitemap de eventos")
    if not stale and enrichment_alerted:
        recovery_parts.append("enriquecimiento automático")
    next_state = {
        "sitemap_failures": failures,
        "sitemap_alerted": (not sitemap_ok) and (sitemap_alerted or failures >= 2),
        "enrichment_alerted": stale,
    }
    if alert_parts:
        return next_state, "🚨 DParranda · Incidencia SEO\n" + "\n".join("• " + s for s in alert_parts)
    if recovery_parts:
        return next_state, "✅ DParranda · SEO recuperado\n" + ", ".join(recovery_parts)
    return next_state, None


def weekly(now, *, session=requests, token="", chat="", dry_run=False,
           state_path=WEEKLY_STATE, db_path=SQLITE_FILE):
    previous = read_json(state_path)
    week = week_ending(now)
    if previous.get("week_ending") == week:
        print("Informe SEO semanal ya entregado para " + week + "; no se duplica.")
        return 0
    try:
        eligible = get_sitemap(session=session)
        active = get_catalog(session=session)
    except (requests.RequestException, ValueError, TypeError) as error:
        print("No se enviará un informe con datos incompletos: " + type(error).__name__)
        return 1
    improved = verified_last_week(db_path, utc(now) - dt.timedelta(days=7), active)
    snapshot = weekly_data(now, eligible, active, previous, improved)
    message = make_weekly_message(snapshot)
    if dry_run:
        print(message)
        return 0
    if not send(token, chat, message):
        print("No se guardará el informe porque Telegram no confirmó su entrega.")
        return 1
    save_json(state_path, snapshot)
    print("Informe SEO entregado y estado guardado: " + week)
    return 0


def health(now, *, session=requests, token="", chat="", dry_run=False,
           state_path=MONITOR_STATE, report_path=ENRICHMENT_STATUS):
    old = read_json(state_path)
    try:
        get_sitemap(session=session)
        healthy = True
    except (requests.RequestException, ValueError, TypeError):
        # A second immediate request avoids counting momentary network errors.
        try:
            get_sitemap(session=session)
            healthy = True
        except (requests.RequestException, ValueError, TypeError):
            healthy = False
    state, message = monitor_result(now, read_json(report_path), healthy, old)
    if dry_run:
        print(message or "Comprobación SEO: sin avisos nuevos.")
        print(json.dumps(state, ensure_ascii=False))
        return 0
    if message and not send(token, chat, message):
        print("Aviso SEO no entregado; se reintentará.")
        return 1
    # When healthy from the start, no tracked monitor state is necessary.
    if state != old and (state["sitemap_failures"] or state["sitemap_alerted"]
                         or state["enrichment_alerted"] or old):
        save_json(state_path, state)
    print("Comprobación SEO terminada; " + ("aviso enviado." if message else "sin avisos nuevos."))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--weekly", action="store_true")
    group.add_argument("--health", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    now = dt.datetime.now(dt.timezone.utc)
    if args.weekly:
        return weekly(now, token=token, chat=chat, dry_run=args.dry_run)
    return health(now, token=token, chat=chat, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
