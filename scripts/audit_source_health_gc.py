"""Continuous quality audit for official CanaryEvent source ingestion.

Separate technical source errors from incomplete facts. An idle Cabildo
recheck (zero URLs due in a 48-hour window) is not a scraper failure.
Input is the published catalogue and two withheld-review queues; no
additional web calls or personally identifying visitor information.
"""
from __future__ import annotations
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
APPROVED="public/events.json"
METADATA="public/meta.json"
VENUE_QUEUE="data/venue_review_gc.json"
PROGRAM_QUEUE="data/program_review_gc.json"
OUTPUT="data/source_quality_gc.json"

def normalize(s):
    val=unicodedata.normalize("NFKD",str(s or "")).casefold()
    return re.sub(r"\W+"," ","".join(c for c in val if not unicodedata.combining(c))).strip()

def due_state(row):
    if row.get("error"):return "error"
    name=row.get("source","")
    if "Portal oficial de Eventos Gran Canaria (Cabildo)"==name:
        if row.get("scanned")==0 and row.get("skipped_recent",0)>0 and row.get("due_urls")==0:
            return "al_dia_sin_fichas_pendientes"
    if "índice de programas PDF" in name:
        return "inventario_documental_no_desglosado"
    if row.get("found",0)==0:
        return "sin_resultados_en_esta_revision"
    return "operativa"

def build_quality(meta,events,venue_queue,program_queue):
    hidden=venue_queue.get("events",[])
    programs=program_queue.get("pending_programs",[])
    errs=[{"source":x["source"],"error":str(x["error"])[:250]} for x in meta.get("sources",[]) if x.get("error")]
    by_source=defaultdict(lambda:{"publicados":0,"recinto_sin_verificar":0,"precio_sin_confirmar":0,
                                  "distancia_al_centro_municipal":0})
    for e in events:
        item=by_source[e.get("source_name") or "Sin fuente"]
        item["publicados"]+=1
        item["precio_sin_confirmar"]+=int(not e.get("price") and e.get("free")!=1)
        item["distancia_al_centro_municipal"]+=int(e.get("accuracy")=="municipality")
    for e in hidden:by_source[e.get("source_name") or "Sin fuente"]["recinto_sin_verificar"]+=1
    sources=[{**{"source":row.get("source"),"estado":due_state(row)},
              **by_source.get(row.get("source"),{"publicados":0,"recinto_sin_verificar":0,
                                                "precio_sin_confirmar":0,"distancia_al_centro_municipal":0}),
              "fichas_leidas_en_esta_ejecucion":row.get("found",0),
              "error":str(row.get("error") or "")[:250]} for row in meta.get("sources",[])]
    # A title+day+municipality match alone is only a possible duplicate:
    # different event sessions may share their heading. Never auto-delete.
    groups=defaultdict(list)
    for e in events:
        groups[(normalize(e.get("title")),str(e.get("start") or "")[:10],
                normalize(e.get("municipality")))].append(e)
    possible=[group for group in groups.values() if len(group)>1]
    pending_review=meta.get("counts",{}).get("needs_review",len(programs))
    cnt={"publicados":len(events),"recintos_sin_verificar":len(hidden),
         "programas_y_fichas_por_revisar":pending_review,
         "precios_sin_confirmar":sum(x["precio_sin_confirmar"] for x in by_source.values()),
         "distancia_a_centro_municipal":sum(x["distancia_al_centro_municipal"] for x in by_source.values()),
         "fuentes_con_error":len(errs),"duplicados_potenciales":len(possible)}
    ordered=sorted(by_source.items(),key=lambda kv:-kv[1]["recinto_sin_verificar"])
    # Unsorted administrative concerns should remain distinguishable from true faults.
    return {"checked_at":meta.get("checked_at"),"quality_counts":cnt,
       "sources":sources,"reported_errors":errs,
       "missing_venue_by_source":[{"source":k,"count":v["recinto_sin_verificar"]}
                                   for k,v in ordered if v["recinto_sin_verificar"]],
       "upcoming_venue_review":[{k:e.get(k) for k in
            ("id","title","start","municipality","source_name","source_url")} for e in
            sorted(hidden,key=lambda x:str(x.get("start") or ""))[:25]],
       "guidance":[
         "Un found=0 no implica necesariamente una fuente rota; comprobar scanned/due_urls/skipped_recent.",
         "Una actividad sin precio confirmado no debe tratarse automáticamente como gratuita.",
         "Las distancias marcadas municipality indican el centro del municipio, no el recinto exacto.",
         "Los eventos sin recinto confirmado permanecen en revisión; no atribuirles un lugar supuesto.",
         "Una coincidencia de título, día y municipio no prueba duplicidad si existen varias sesiones."
       ]}

def main():
    def read(path):return json.loads((ROOT/path).read_text(encoding="utf8"))
    report=build_quality(read(METADATA),read(APPROVED)["events"],read(VENUE_QUEUE),read(PROGRAM_QUEUE))
    dst=ROOT/OUTPUT
    dst.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("SOURCE_QUALITY",report["checked_at"],report["quality_counts"])
    print("MISSING_VENUE_BY_SOURCE",report["missing_venue_by_source"])
    return 0

if __name__=="__main__":raise SystemExit(main())
