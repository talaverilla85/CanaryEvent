#!/usr/bin/env python3
"""Import DParranda SQLite/catalog into PostgreSQL without switching the live site.

Use the DATABASE_URL environment variable; never pass credentials as arguments.
The import is transactional, repeatable, and preserves manual editorial overrides.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE = ROOT / "data" / "events.sqlite"
SCHEMA = ROOT / "sql" / "postgres_schema.sql"
PUBLIC_EVENTS = ROOT / "public" / "events.json"
PUBLIC_ADS = ROOT / "public" / "ads.json"

EVENT_COLUMNS = (
    "id", "dedup_key", "title", "start", "end", "municipality", "venue",
    "category", "free", "price", "details", "lat", "lng", "accuracy",
    "source_name", "source_url", "status", "image_url", "image_alt",
    "image_origin", "image_status", "organizer_url", "created_at",
    "updated_at", "last_seen",
)
SOURCE_COLUMNS = ("source", "checked_at", "found", "added", "changed", "error")
AD_COLUMNS = (
    "id", "enabled", "advertiser", "kind", "permanent", "starts_at",
    "ends_at", "municipalities", "headline", "description", "location",
    "button_text", "button_url", "image", "image_alt", "disclosure",
)


def read_snapshot():
    """Read SQLite source rows, public occurrence cards and advertising seed."""
    if not SQLITE.is_file():
        raise RuntimeError("No existe data/events.sqlite")
    with sqlite3.connect("file:" + str(SQLITE) + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(x) for x in db.execute("SELECT * FROM events")]
        logs = [dict(x) for x in db.execute("SELECT * FROM source_log")]
    for row in rows:
        missing = set(EVENT_COLUMNS) - set(row)
        if missing:
            raise RuntimeError("SQLite no incluye columnas: " + ", ".join(sorted(missing)))
    catalogue = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
    advertising = json.loads(PUBLIC_ADS.read_text(encoding="utf-8"))
    cards = catalogue.get("events", [])
    campaigns = advertising.get("ads", [])
    if not isinstance(cards, list) or not isinstance(campaigns, list):
        raise RuntimeError("Formato incorrecto de events.json o ads.json")
    if len({int(e["id"]) for e in cards}) != len(cards):
        raise RuntimeError("ID de ficha duplicado en el catálogo público")
    return rows, logs, catalogue, cards, campaigns


def names_sql(columns):
    # Names are exclusively from the module constants, never external input.
    return ", ".join('"' + column + '"' for column in columns)


def import_snapshot(connection, rows, logs, catalogue, cards, campaigns):
    from psycopg.types.json import Jsonb

    with connection.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
        # Initialize commercial campaigns, private invoicing and image tables in a fresh database.
        cur.execute((ROOT / "sql" / "advertising_v2.sql").read_text(encoding="utf-8"))
        event_update = ", ".join(
            '"' + col + '" = EXCLUDED."' + col + '"'
            for col in EVENT_COLUMNS if col not in ("id", "created_at")
        )
        event_sql = (
            "INSERT INTO events (" + names_sql(EVENT_COLUMNS) + ") VALUES (" +
            ", ".join(["%s"] * len(EVENT_COLUMNS)) + ") "
            "ON CONFLICT(id) DO UPDATE SET " + event_update
        )
        cur.executemany(
            event_sql,
            [tuple(row.get(col) for col in EVENT_COLUMNS) for row in rows],
        )

        log_update = ", ".join(
            '"' + col + '" = EXCLUDED."' + col + '"'
            for col in SOURCE_COLUMNS if col != "source"
        )
        log_sql = (
            "INSERT INTO source_log (" + names_sql(SOURCE_COLUMNS) + ") VALUES (" +
            ", ".join(["%s"] * len(SOURCE_COLUMNS)) + ") "
            "ON CONFLICT(source) DO UPDATE SET " + log_update
        )
        cur.executemany(
            log_sql,
            [tuple(row.get(col) for col in SOURCE_COLUMNS) for row in logs],
        )

        cur.executemany(
            """INSERT INTO published_events(id,payload,active,synced_at)
               VALUES(%s,%s,TRUE,now())
               ON CONFLICT(id) DO UPDATE SET
                   payload=EXCLUDED.payload,active=TRUE,synced_at=now()""",
            [(int(card["id"]), Jsonb(card)) for card in cards],
        )
        cur.execute(
            "UPDATE published_events SET active=FALSE "
            "WHERE NOT(id = ANY(%s::bigint[]))",
            ([int(card["id"]) for card in cards],),
        )

        ads_sql = (
            "INSERT INTO ad_campaigns (" + names_sql(AD_COLUMNS) + ") VALUES (" +
            ", ".join(["%s"] * len(AD_COLUMNS)) + ") ON CONFLICT(id) DO NOTHING"
        )
        cur.executemany(
            ads_sql,
            [
                tuple(
                    Jsonb(ad.get(col) or []) if col == "municipalities"
                    else ad.get(col)
                    for col in AD_COLUMNS
                )
                for ad in campaigns
            ],
        )
        cur.execute(
            """INSERT INTO catalog_sync(id,generated_at,event_count)
               VALUES(1,%s,%s)
               ON CONFLICT(id) DO UPDATE SET
                   generated_at=EXCLUDED.generated_at,
                   event_count=EXCLUDED.event_count,updated_at=now()""",
            (catalogue.get("generated_at"), len(cards)),
        )

        cur.execute(
            "SELECT count(*) FROM events WHERE id = ANY(%s::bigint[])",
            ([int(row["id"]) for row in rows],),
        )
        present = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM published_events WHERE active")
        active = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM ad_campaigns")
        ads = cur.fetchone()[0]
        if present != len(rows) or active != len(cards):
            raise RuntimeError(
                "Error de paridad: SQLite=%s PostgreSQL=%s, JSON=%s activos=%s"
                % (len(rows), present, len(cards), active)
            )
        return dict(
            sqlite_records=len(rows),
            postgres_verified_records=present,
            published_cards=active,
            ad_campaigns=ads,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="Verificar datos de origen sin conectar con PostgreSQL")
    group.add_argument("--sync", action="store_true",
                       help="Importar y verificar PostgreSQL en una transacción")
    args = parser.parse_args()

    rows, logs, catalogue, cards, campaigns = read_snapshot()
    print(
        "Origen: %s registros SQLite, %s fuentes, %s fichas, %s anuncios"
        % (len(rows), len(logs), len(cards), len(campaigns))
    )
    if args.check:
        return 0

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL no configurada: web y SQLite sin cambios")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Instalar dependencias de scripts/requirements.txt") from exc
    # The provider connection URL configures TLS. Never log the URL.
    with psycopg.connect(dsn, connect_timeout=15) as db:
        result = import_snapshot(db, rows, logs, catalogue, cards, campaigns)
    print("Importación verificada: " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
