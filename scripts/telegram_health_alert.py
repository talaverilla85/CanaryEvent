"""Notify CanaryEvent operations through Telegram after the sync workflow ends.

Never log or persist the bot token. The watcher runs separately via workflow_run,
so a failed/timed-out importer can still trigger an alert.
Daily source warnings: schedule + dispatch only, not every development push.
Workflow failure: any run (including push) merits notification.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests

ROOT=Path(__file__).resolve().parents[1]
QUALITY=ROOT/"data"/"source_quality_gc.json"
META=ROOT/"public"/"meta.json"
MAX_SOURCES=7

def parse_date(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(dt.timezone.utc)
    except (ValueError,TypeError,AttributeError):
        return None

def same_run(report_time, started, finished):
    checked=parse_date(report_time)
    began=parse_date(started)
    ended=parse_date(finished)
    # Require timestamps from this exact run. No old cached audit messages.
    if not all((checked,began,ended)):
        return False
    tolerance=dt.timedelta(minutes=3)
    return began-tolerance<=checked<=ended+tolerance

def safe_line(text):
    return re.sub(r"[\r\n\t]+"," ",str(text or "").strip())[:105]

def normalize_errors(quality):
    entries=quality.get("reported_errors",[])
    return list(dict.fromkeys(
        (safe_line(row.get("source")),safe_line(row.get("error")))
        for row in entries if row.get("source") and row.get("error")
    ))

def make_message(*,conclusion,event,url,started,finished,quality,meta):
    status=str(conclusion or "").lower()
    if status not in ("success","failure","cancelled","timed_out","action_required","skipped","neutral","stale"):
        status="unknown"
    scheduled=event in ("schedule","workflow_dispatch")
    is_failure=status!="success"
    fresh=(same_run(quality.get("checked_at"),started,finished)
           and same_run(meta.get("checked_at"),started,finished))
    errors=normalize_errors(quality) if fresh else []
    # A push that completed but has noncritical source warnings is suppressed
    # to avoid repeating the same message while editing the application.
    if not is_failure and not scheduled:
        return None
    if not is_failure and not fresh:
        lines=["⚠️ ¿Pa' Dónde? · No se pudo validar el informe diario",
               "El flujo terminó correctamente, pero el informe de calidad no pertenece a esta ejecución."]
    elif not is_failure and not errors:
        return None
    elif is_failure:
        lines=["🚨 ¿Pa' Dónde? · Falló la actualización automática",
               "Estado de GitHub: "+safe_line(status)]
        if fresh and errors:
            lines.append("Fuentes con incidencias: "+str(len(errors)))
    else:
        lines=["⚠️ ¿Pa' Dónde? · Problemas con "+str(len(errors))+" fuentes",
               "La sincronización general terminó, pero algunos conectores fallaron."]
    if fresh and errors:
        for name,error in errors[:MAX_SOURCES]:
            lines.append("• "+name+" — "+error[:60])
        if len(errors)>MAX_SOURCES:
            lines.append("• Y "+str(len(errors)-MAX_SOURCES)+" más")
    if fresh:
        count=meta.get("counts",{}).get("approved")
        if isinstance(count,int):
            lines.append("Eventos públicos: "+str(count))
    if url.startswith("https://github.com/") and "/actions/runs/" in url:
        lines.append("Revisar: "+url[:240])
    return "\n".join(lines)[:3800]

def send(bot_token,chat_id,message,*,session=requests):
    if not bot_token or not chat_id:
        print("Telegram no configurado: añade ambos secretos TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
        return False
    try:
        response=session.post(
            "https://api.telegram.org/bot"+bot_token+"/sendMessage",
            json={"chat_id":chat_id,"text":message,
                  "link_preview_options":{"is_disabled":True}},
            timeout=15)
        # Never call raise_for_status: requests exceptions include a URL
        # containing the secret in their stringification.
        if response.status_code!=200:
            print("Telegram rechazó el aviso (HTTP "+str(response.status_code)+").")
            return False
        payload=response.json()
        if payload.get("ok") is not True:
            print("Telegram no confirmó el envío.")
            return False
        print("Telegram confirmó el envío del aviso.")
        return True
    except (requests.RequestException,ValueError) as err:
        print("Error seguro enviando a Telegram: "+type(err).__name__)
        return False

def load_report(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError,ValueError,TypeError):
        return {}

def run(environ=None,*,test=False):
    env=os.environ if environ is None else environ
    token=env.get("TELEGRAM_BOT_TOKEN","").strip()
    chat=env.get("TELEGRAM_CHAT_ID","").strip()
    if test:
        message=("✅ ¿Pa' Dónde? · Telegram conectado\n"
                 "Prueba enviada desde GitHub Actions. Los avisos reales se enviarán solo si hay incidencias.")
    else:
        quality=load_report(QUALITY)
        meta=load_report(META)
        message=make_message(
            conclusion=env.get("SOURCE_RUN_CONCLUSION",""),
            event=env.get("SOURCE_RUN_EVENT",""),
            url=env.get("SOURCE_RUN_URL",""),
            started=env.get("SOURCE_RUN_STARTED_AT",""),
            finished=env.get("SOURCE_RUN_FINISHED_AT",""),
            quality=quality,meta=meta)
    if not message:
        print("No hay incidencias notificables en esta ejecución.")
        return 0
    if not token or not chat:
        print("Telegram pendiente de configurar. No se envió el aviso.")
        return 1 if test else 0
    # An invalid Telegram credential should fail the monitor job, not the
    # data ingestion job. Bot API HTTP responses are not logged.
    return 0 if send(token,chat,message) else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--test",action="store_true")
    args=parser.parse_args()
    raise SystemExit(run(test=args.test))
