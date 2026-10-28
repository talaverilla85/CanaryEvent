"""Auditable island-by-island culture source coverage.

Prepared for all Canary Islands. Until an island has its municipality +
venue mapping reviewed, discovery is allowed but PUBLICATION is disabled.
This report can be generated daily after the official event export.
"""
from __future__ import annotations
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"data"/"island_source_registry.json"
EVENTS=ROOT/"public"/"events.json"
META=ROOT/"public"/"meta.json"
OUTPUT=ROOT/"public"/"island_source_status.json"

def data(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError,ValueError):return default

def build(registry,events,meta,date):
    targets=registry["island_targets"]
    active=set(registry["active_publication_islands"])
    if len(targets)!=8 or len(targets)!=len(set(targets)) or any(x not in targets for x in active):
        raise ValueError("Eight unique Canary Island targets required")
    required={"source_url oficial permitido","fecha comprobada","isla exacta",
              "municipio y recinto comprobados"}
    if not required.issubset(set(registry["publish_requirements"])):
        raise ValueError("Missing essential island publication safeguards")
    source_logs={x.get("source"):x for x in meta.get("sources",[])}
    card_counts=Counter(e.get("source_name") for e in events.get("events",[]))
    sources=[]
    for item in registry["source_profiles"]:
        log=source_logs.get(item["name"])
        sources.append({
            "id":item["id"],"name":item["name"],"type":item["type"],
            "url":item["url"],"islands":item["islands"],
            "status":item["status"],"adapter":item["adapter"],
            "found_last_run":log.get("found") if log else None,
            "last_error":log.get("error") if log else None,
            "published_cards":card_counts[item["name"]],
            "has_live_connector":log is not None,
        })
    tracked=[]
    for e in events.get("events",[]):
        if "camino viejo producciones" in str(e.get("details","")).casefold():
            tracked.append({"title":e["title"],"date":str(e.get("start",""))[:10],
                            "venue":e.get("venue",""),
                            "municipality":e.get("municipality",""),
                            "official_url":e.get("source_url","")})
    return {
        "checked_on":date.isoformat(),
        "active_publication_islands":sorted(active),
        "islands":[{"island":name,"publication_enabled":name in active,
                    "mapping_status":registry["island_bootstrap"][name]["publication"],
                    "sources_registered":sum(name in s["islands"] for s in sources)}
                   for name in targets],
        "source_count":len(sources),"sources":sources,
        "producer_observations":{
            "Camino Viejo Producciones":tracked,
            "method":"Credit explicitly present in an official venue listing, not assumed from production title"
        },
        "next_island_requirements":[
            "Map all municipalities and their island identities",
            "Build a validated venue directory and coordinates",
            "Confirm source policies, current programme and per-island filters",
            "Run duplicate and year-scoping tests before changing publication_enabled",
        ],
        "security":"No unverified events published outside Gran Canaria",
    }

def run():
    today=dt.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    report=build(data(REGISTRY,{}),data(EVENTS,{}),data(META,{}),today)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    tmp.replace(OUTPUT)
    print("Island cultural sources:",report["source_count"],
          "Camino Viejo credited:",len(report["producer_observations"]["Camino Viejo Producciones"]))
    return report

if __name__=="__main__":run()
