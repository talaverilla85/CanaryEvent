#!/usr/bin/env python3
"""DParranda: alert the private Telegram chat of incoming ad requests and paid campaigns.

GitHub Actions holds the database and Telegram credentials; never expose them
to the browser. No personal contact details or tax data are sent. Polls about
every five minutes and records successful deliveries to avoid repeat alerts.
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


def clean(value,limit=80):
    """Plain-text fields only: Telegram never receives emails, phones or fiscal data."""
    return re.sub(r"[\r\n\t]+"," ",str(value or "").strip())[:limit]


def make_message(number,info,*,company="",title="",zone="",start="",review_status=""):
    match=INTEREST_TAG.fullmatch(str(info or ""))
    if not match or not isinstance(number,int) or number<1:
        return None
    plan,total,days,kind=match.groups()
    submitted=review_status=="submitted"
    lines=[
        "📣 DParranda · Nueva solicitud de publicidad" if submitted
        else "📣 DParranda · Nuevo anunciante interesado",
        "Solicitud #"+str(number),
    ]
    if company:
        lines.append("Negocio: "+clean(company,100))
    if title:
        lines.append("Campaña: "+clean(title,130))
    lines.extend([
        "Plan: "+PLANS[plan]+" · "+days+" días · "+total+" €",
        "Formato: "+("Banner" if kind=="banner" else "Evento patrocinado"),
    ])
    if zone:
        lines.append("Cobertura: "+clean(zone,130))
    if start:
        lines.append("Inicio solicitado: "+clean(start,10))
    lines.append("Estado: pendiente de revisión" if submitted else "Estado: interés inicial")
    lines.append("Revisar en el panel privado:\n"+PANEL_URL)
    return "\n".join(lines)


def make_payment_message(row):
    """Only signed Stripe payments saved and scheduled by the backend qualify."""
    if len(row)!=11:
        return None
    (number,advertiser,title,plan,days,placement,cents,locations,
     start,end,session_id)=row
    if not isinstance(number,int) or number<1 or plan not in PLANS or days not in (30,60):
        return None
    if placement not in ("banner","evento") or type(cents) is not int or cents<1:
        return None
    if not re.fullmatch(r"cs_(test|live)_[A-Za-z0-9]+",str(session_id or "")):
        return None
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",str(start or "")) or \
       not re.fullmatch(r"20\d{2}-\d{2}-\d{2}",str(end or "")) or end<start:
        return None
    sandbox=str(session_id).startswith("cs_test_")
    coverage=", ".join(clean(v,45) for v in locations[:4] if isinstance(v,str)) \
        if isinstance(locations,list) else ""
    amount=f"{cents/100:.2f}".replace(".",",")+" €"
    lines=[
        "🧪 DParranda · Pago de PRUEBA confirmado (Stripe Test)" if sandbox
        else "💶 DParranda · PAGO CONFIRMADO",
        "Contrato #"+str(number),
        "Negocio: "+clean(advertiser,100),
        "Campaña: "+clean(title,130),
        "Servicio: "+PLANS[plan]+" · "+("Banner" if placement=="banner" else "Evento patrocinado"),
        "Cobertura: "+(coverage or "Toda Gran Canaria"),
        "Duración: "+str(days)+" días",
        "Importe: "+amount,
        "Inicio: "+start[8:10]+"/"+start[5:7]+"/"+start[:4],
        "Fin: "+end[8:10]+"/"+end[5:7]+"/"+end[:4],
        "Estado: pago confirmado; fechas programadas",
    ]
    if sandbox:
        lines.append("PRUEBA · No se ha cobrado ni publicado un anuncio real.")
    lines.append("Ver contrato en el panel:\n"+PANEL_URL)
    return "\n".join(lines)

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
          SELECT e.id,e.dates_text,e.company,e.campaign_name,e.municipality,
                 to_char(e.campaign_start,'YYYY-MM-DD'),e.review_status
          FROM advertising_enquiries e
          LEFT JOIN advertising_interest_notifications n ON n.enquiry_id=e.id
          WHERE e.dates_text LIKE 'INTERES_INICIAL|%%' AND n.enquiry_id IS NULL
          ORDER BY e.created_at,e.id LIMIT %s
        """,(MAX_PER_RUN,))
        rows=cur.fetchall()
    total=0
    for row in rows:
        number,info=row[:2]
        extra=list(row[2:])+[""]*5
        company,title,zone,start,review_status=extra[:5]
        message=make_message(int(number),info,company=company,title=title,
                             zone=zone,start=start,review_status=review_status)
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


def poll_payments(sql,token,chat,send_message=send):
    """Once per paid draft; only after Stripe confirmation and scheduling."""
    with sql.cursor() as cur:
        cur.execute("""
          CREATE TABLE IF NOT EXISTS advertising_payment_notifications (
            draft_id BIGINT PRIMARY KEY REFERENCES advertiser_campaign_drafts(id) ON DELETE CASCADE,
            notified_at TIMESTAMPTZ NOT NULL DEFAULT now()
          )
        """)
        cur.execute("""
          SELECT d.id,d.advertiser,d.title,d.plan,d.days,d.placement,
                 d.price_cents,d.municipalities,
                 to_char(d.actual_starts_at,'YYYY-MM-DD'),
                 to_char(d.actual_ends_at,'YYYY-MM-DD'),
                 d.stripe_checkout_session_id
          FROM advertiser_campaign_drafts d
          LEFT JOIN advertising_payment_notifications n ON n.draft_id=d.id
          WHERE d.payment_status='paid' AND d.paid_at IS NOT NULL
            AND d.actual_starts_at IS NOT NULL AND d.actual_ends_at IS NOT NULL
            AND d.stripe_checkout_session_id ~ '^cs_(test|live)_[A-Za-z0-9]+$'
            AND n.draft_id IS NULL
          ORDER BY d.paid_at,d.id LIMIT %s
        """,(MAX_PER_RUN,))
        rows=cur.fetchall()
    total=0
    for row in rows:
        message=make_payment_message(row)
        if message is None:
            print("Pago confirmado con datos inesperados; revisar en panel")
            continue
        if not send_message(token,chat,message):
            print("Aviso de pago no entregado; se reintentará")
            return total,False
        with sql.cursor() as cur:
            cur.execute("""
              INSERT INTO advertising_payment_notifications(draft_id)
              VALUES (%s) ON CONFLICT DO NOTHING
            """,(row[0],))
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
            paid_count,paid_ok=poll_payments(sql,token,chat,send_message=send_message)
        print("Solicitudes notificadas:",count,"; pagos confirmados notificados:",paid_count)
        return 0 if ok and paid_ok else 1
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
