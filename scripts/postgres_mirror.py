#!/usr/bin/env python3
"""Safely mirror DParranda SQLite and public catalog to PostgreSQL.
Run after sync_events.py. Never changes the live JSON and never prints secrets.
"""
import json
import os
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COLUMNS=("id","dedup_key","title","start","end","municipality","venue","category","free","price","details","lat","lng","accuracy","source_name","source_url","status","image_url","image_alt","image_origin","image_status","organizer_url","created_at","updated_at","last_seen")
SRC_COLS=("source","checked_at","found","added","changed","error")
AD_COLS=("id","enabled","advertiser","kind","permanent","starts_at","ends_at","municipalities","headline","description","location","button_text","button_url","image","image_alt","disclosure")

def read_source():
 with sqlite3.connect(f"file:{ROOT/'data/events.sqlite'}?mode=ro",uri=True) as conn:
  conn.row_factory=sqlite3.Row
  rows=[dict(r) for r in conn.execute("SELECT * FROM events")]
  logs=[dict(r) for r in conn.execute("SELECT * FROM source_log")]
 catalog=json.loads((ROOT/"public/events.json").read_text(encoding="utf8"))
 ads=json.loads((ROOT/"public/ads.json").read_text(encoding="utf8"))
 cards=catalog["events"]
 if len({int(e["id"]) for e in cards})!=len(cards):raise RuntimeError("IDs de fichas duplicados")
 return rows,logs,catalog,cards,ads["ads"]

def sync(dsn):
 import psycopg
 from psycopg.types.json import Jsonb
 rows,logs,catalog,cards,ads=read_source()
 with psycopg.connect(dsn,connect_timeout=15) as db:
  with db.cursor() as cur:
   cols=",".join('"'+c+'"' for c in COLUMNS)
   values=",".join(["%s"]*len(COLUMNS))
   updates=",".join('"'+c+'"=excluded."'+c+'"' for c in COLUMNS if c not in ("id","created_at"))
   cur.executemany(f"INSERT INTO events ({cols}) VALUES ({values}) ON CONFLICT(id) DO UPDATE SET {updates}",[tuple(e.get(c) for c in COLUMNS) for e in rows])
   cur.executemany("INSERT INTO source_log(source,checked_at,found,added,changed,error) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(source) DO UPDATE SET checked_at=excluded.checked_at,found=excluded.found,added=excluded.added,changed=excluded.changed,error=excluded.error",[tuple(e.get(c) for c in SRC_COLS) for e in logs])
   cur.executemany("INSERT INTO published_events(id,payload,active,synced_at) VALUES(%s,%s,TRUE,now()) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,active=TRUE,synced_at=now()",[(int(e["id"]),Jsonb(e)) for e in cards])
   cur.execute("UPDATE published_events SET active=FALSE WHERE NOT (id=ANY(%s::bigint[]))",([int(e["id"]) for e in cards],))
   for a in ads:
    cur.execute("INSERT INTO ad_campaigns(id,enabled,advertiser,kind,permanent,starts_at,ends_at,municipalities,headline,description,location,button_text,button_url,image,image_alt,disclosure) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",(a["id"],a.get("enabled",False),a["advertiser"],a.get("kind","paid"),a.get("permanent",False),a.get("starts_at"),a.get("ends_at"),Jsonb(a.get("municipalities",[])),a["headline"],a.get("description",""),a.get("location",""),a.get("button_text","Descubrir"),a["button_url"],a.get("image",""),a.get("image_alt",""),a.get("disclosure","Publicidad")))
   cur.execute("INSERT INTO catalog_sync(id,generated_at,event_count) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET generated_at=excluded.generated_at,event_count=excluded.event_count,updated_at=now()",(catalog.get("generated_at"),len(cards)))
   cur.execute("SELECT count(*) FROM published_events WHERE active")
   actual=cur.fetchone()[0]
   if actual!=len(cards):raise RuntimeError(f"Catálogo incompleto PostgreSQL={actual} JSON={len(cards)}")
 print(f"PostgreSQL sincronizado: {len(rows)} originales, {len(cards)} fichas, {len(logs)} fuentes")

if __name__=="__main__":
 dsn=os.environ.get("DPARRANDA_DATABASE_URL")
 if not dsn:
  raise SystemExit("DPARRANDA_DATABASE_URL no configurada; no se han modificado datos")
 sync(dsn)
