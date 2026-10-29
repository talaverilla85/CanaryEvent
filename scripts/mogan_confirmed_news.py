"""Event-specific verified municipal press notice from Ayuntamiento de Mogán.

Not a general "events by township" scraper. The named 2026 date,
clock and venue were verified from the town's official 27 October press
release. The original site has intermittent automated-access failures;
do not turn an inaccessible page into an invented time/place.
"""
import datetime as dt

NAME="Ayuntamiento de Mogán · actividades documentadas"
MUNICIPALITY="Mogán"
NOTICE="https://mogan.es/es/Noticias/mogan-celebrara-el-dia-de-la-infancia-con-una-aventura-marinera-llena-de-juegos-y-talleres"
EVENTS=(
 dict(title="Día de la Infancia · Aventuras en el mar",day="2026-11-14",
      time="10:00",venue="Plaza Pérez Galdós, Arguineguín",
      category="familia",free=1,
      details="Jornada familiar gratuita organizada por el Ayuntamiento de Mogán: pasacalle, juegos y talleres infantiles. El pasacalle parte a las 10:00 y el programa continúa en la plaza."),
)
def fetch_and_extract(today,places):
    if MUNICIPALITY not in places:return [],{"source":NAME,"found":0,"error":""}
    entries=[]
    for e in EVENTS:
        day=dt.date.fromisoformat(e["day"])
        if day<today or day>today+dt.timedelta(days=120):continue
        entries.append({
            "title":e["title"],"start":e["day"]+"T"+e["time"]+":00",
            "end":None,"municipality":MUNICIPALITY,
            "venue":e["venue"],"category":e["category"],
            "free":e["free"],"price":"Gratis",
            "details":e["details"],
            "source_name":NAME,"source_url":NOTICE,"status":"approved"})
    return entries,{"source":NAME,"found":len(entries),"error":"",
                    "method":"official_27_october_2026_notice_verified"}
