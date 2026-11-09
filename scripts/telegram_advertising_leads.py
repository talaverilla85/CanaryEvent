#!/usr/bin/env python3
"""DParranda: notify the existing Telegram bot of new commercial-interest leads.

Database and Telegram credentials are GitHub Actions secrets, never the browser.
Only request IDs and package types enter Telegram; customer contacts stay in
the authenticated admin panel. Poll at roughly five-minute intervals.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import psycopg
from telegram_health_alert import send

INTEREST_TAG=re.compile(r"^INTERES_INICIAL\|(local|zona|insular)\|([0-9]+)\|(30|60)\|(banner|evento)$")
PLANS={"local":"Local","zona":"Zona","insular":"Insular"}
MAX_PER_RUN=15
PANEL_URL="https://canaryevent.vercel.app/admin/#publicidad"


def make_message(number,info):
    match=INTEREST_TAG.fullmatch(str(info or ""))
    if not match or not isinstance(number,int) or number<1:
        return None
    plan,total,days,kind=match.groups()
    return ("📣 DParranda · Nuevo anunciante interesado\n"
            "Solicitud #"+str(number)+"\n"
            "Plan: "+PLANS[plan]+" · "+days+" días · "+total+" €\n"
            "Formato: "+("Banner" if kind=="banner" else "Evento patrocinado")+"\n"
            "Consulta los datos de contacto en el panel:\n"+PANEL_URL)


def poll(sql,token,chat,send_message=send):
    """Mark an alert delivered only after Telegram confirms it."""
    with sql.cursor() as cur:
        cur.execute("""
          CREATE TABLE IF NOT EXISTS advertising_interest_notifications (
            enquiry_id BIGINT PRIMARY KEY REFERENCES advertising_enquiries(id) ON DELETE CASCADE,
            notified_at TIMESTAMPTZ NOT NULL DEFAULT now()
          )
        """)
        cur.execute("""
          SELECT e.id,e.dates_text
          FROM advertising_enquiries e
          LEFT JOIN advertising_interest_notifications n ON n.enquiry_id=e.id
          WHERE e.dates_text LIKE 'INTERES_INICIAL|%%' AND n.enquiry_id IS NULL
          ORDER BY e.created_at,e.id LIMIT %s
        """,(MAX_PER_RUN,))
        rows=cur.fetchall()
    total=0
    for number,info in rows:
        message=make_message(int(number),info)
        if message is None:
            # Malformed data should never be sent without validation.
            print("Solicitud con formato inesperado; revisar desde el panel")
            continue
        if not send_message(token,chat,message):
            print("Aviso no entregado: se conservará pendiente para el siguiente intento")
            return total,False
        with sql.cursor() as cur:
            cur.execute("""
              INSERT INTO advertising_interest_notifications(enquiry_id)
              VALUES (%s) ON CONFLICT DO NOTHING
            """,(number,))
        total+=1
    return total,True


def run(env=None,*,test=False,connect=psycopg.connect,send_message=send):
    env=env or os.environ
    token=env.get("TELEGRAM_BOT_TOKEN","").strip()
    chat=env.get("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:
        print("Bot de interesados pendiente: configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
        return 1
    if test:
        message=("✅ DParranda · Avisos de anunciantes conectados\n"
                 "Las nuevas solicitudes se guardarán en el panel privado.\n"+PANEL_URL)
        return 0 if send_message(token,chat,message) else 1
    database=env.get("DATABASE_URL","").strip()
    if not database:
        print("Monitor de interesados sin conexión a la base de datos")
        return 1
    try:
        with connect(database,connect_timeout=12,autocommit=True) as sql:
            count,ok=poll(sql,token,chat,send_message=send_message)
        print("Notificaciones de interesados confirmadas:",count)
        return 0 if ok else 1
    except psycopg.Error as exc:
        # Never print connection strings or customer records.
        print("No se pudo consultar la base privada:",type(exc).__name__)
        return 1


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--test",action="store_true",help="Send a harmless test to the configured chat")
    args=parser.parse_args()
    raise SystemExit(run(test=args.test))


if __name__=="__main__":
    main()
