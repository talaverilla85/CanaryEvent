"""Transparent per-municipality coverage for Gran Canaria's 21 towns.

This report distinguishes catalog events (also from Cabildo and box offices)
from individual acts actually supplied by that town hall. No town is labelled
fully covered solely because it appears in the combined events catalog.
"""
from __future__ import annotations
from collections import Counter
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data"/"municipal_sources_gc.json"
META=ROOT/"public"/"meta.json"
EVENTS=ROOT/"public"/"events.json"
TARGET=ROOT/"public"/"municipal_coverage.json"

def read(path,fallback):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (ValueError,OSError):
        return fallback

def make_report(*,registry=None,metadata=None,catalog=None,today=None):
    registry=registry if registry is not None else read(SRC,{})
    metadata=metadata if metadata is not None else read(META,{})
    catalog=catalog if catalog is not None else read(EVENTS,{})
    today=today or dt.date.today()
    municipalities=registry.get("municipalities",[])
    if len(municipalities)!=21 or len({m.get("municipality") for m in municipalities})!=21:
        raise ValueError("The official Gran Canaria registry must include 21 unique municipalities")
    events=catalog.get("events",[])
    counts=Counter(e.get("municipality") for e in events
                   if isinstance(e,dict) and e.get("status") not in {"cancelled","archived"})
    # A few official local feeds use a department name rather than the
    # canonical "Ayuntamiento ..." source label.
    municipal_department_sources={
        "Las Palmas de Gran Canaria":{"Juventud Las Palmas de Gran Canaria"},
        "Ingenio":{"Juventud de Ingenio · programa de otoño desglosado"},
    }
    municipal_events=Counter(
        e.get("municipality") for e in events
        if isinstance(e,dict) and
        (str(e.get("source_name") or "").startswith(
            ("Ayuntamiento de ","Ayuntamiento ","Ilustre Ayuntamiento"))
         or str(e.get("source_name") or "") in municipal_department_sources.get(
            e.get("municipality"),set()))
        and e.get("status") not in {"cancelled","archived"})
    source_logs=metadata.get("sources",[])
    clean=[]
    for item in municipalities:
        name=item["municipality"]
        from_municipality=municipal_events[name]
        all_events=counts[name]
        declared=item.get("status","por_localizar")
        # Reconciled after the fourth official-news connector was added.
        if name in {"Agaete","Vega de San Mateo","Santa María de Guía","San Bartolomé de Tirajana"}:
            if from_municipality>0:
                declared="conector_parcial_articulos_contrastados"
            else:
                declared="fuente_oficial_contrastada_sin_actos_futuros"
        elif name=="Valleseco":
            declared="agenda_localizada_por_validar_datos"
        signals=[
            {"source":s.get("source"),"found":s.get("found",0),"error":s.get("error","")}
            for s in source_logs
            if name.casefold() in str(s.get("source") or "").casefold()
        ]
        if declared.startswith("conector_activo"):
            coverage="conector_automatico_parcial"
        elif declared.startswith("conector_parcial") or declared.startswith("agenda_localizada") or declared=="programacion_por_verificar":
            coverage="cobertura_parcial_o_en_revision"
        else:
            coverage="sin_extraccion_municipal_automatizada"
        clean.append({
            "municipality":name,
            "official_website":item.get("official_website"),
            "agenda_url":item.get("agenda_url"),
            "original_connector_state":item.get("status"),
            "coverage_level":coverage,
            "data_status":declared,
            "catalog_cards_total":all_events,
            "municipal_cards_total":from_municipality,
            "other_sources_cards_total":max(0,all_events-from_municipality),
            "source_health":signals[:8],
            "full_coverage_claim":False,
        })
    return {
        "updated_on":today.isoformat(),
        "scope":"21 municipios de Gran Canaria",
        "municipalities_total":len(clean),
        "municipalities_with_any_catalog_cards":sum(bool(x["catalog_cards_total"]) for x in clean),
        "municipalities_with_official_municipal_cards":sum(bool(x["municipal_cards_total"]) for x in clean),
        "municipalities_without_municipal_cards":sum(not x["municipal_cards_total"] for x in clean),
        "full_coverage_confirmed":False,
        "important":"Municipal coverage is NOT the same as having third-party events near that town. Partial official connectors do not guarantee every local event.",
        "municipalities":clean,
    }

def run():
    from zoneinfo import ZoneInfo
    report=make_report(today=dt.datetime.now(ZoneInfo("Atlantic/Canary")).date())
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    temp=TARGET.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    temp.replace(TARGET)
    print("CanaryEvent municipality coverage:",
          report["municipalities_with_official_municipal_cards"],"of",
          report["municipalities_total"],"have official municipal cards")
    return report

if __name__=="__main__":
    run()
