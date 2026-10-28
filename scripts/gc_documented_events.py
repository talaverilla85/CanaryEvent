"""Individually corroborated upcoming events from four official municipal articles.

These are fixed, auditable 2026 programme facts, NOT guessed future schedules.
Read the municipal page on every update, require corroborating text, and omit
rows automatically after their event day; expand only after reviewing new facts.
"""
from __future__ import annotations
import datetime as dt
import re
import unicodedata
from collections import defaultdict

SOURCES=(
 {"municipality":"Agaete",
  "url":"https://www.agaete.es/noticias/el-colegio-del-terror",
  "events":[
   {"title":"El Colegio del Terror","date":"2026-10-30","time":"18:30",
    "venue":"Parque Popular","category":"familia","tokens":("30","31","octubre","18:30","Parque Popular","Colegio del Terror"),
    "details":"Actividad de Halloween organizada por Juventud. Menores de 6 a 12 años acompañados por un adulto."},
   {"title":"El Colegio del Terror","date":"2026-10-31","time":"18:30",
    "venue":"Parque Popular","category":"familia","tokens":("30","31","octubre","18:30","Parque Popular","Colegio del Terror"),
    "details":"Actividad de Halloween organizada por Juventud. Menores de 6 a 12 años acompañados por un adulto."}
  ]},
 {"municipality":"Vega de San Mateo",
  "url":"https://vegadesanmateo.es/noticia/vuelve-la-fiesta-de-finaos-vega-de-san-mateo",
  "events":[
   {"title":"Fiesta de Finaos de Vega de San Mateo","date":"2026-10-31","time":"20:30",
    "venue":"Plaza de la Solidaridad","category":"cultura","tokens":("31 de octubre","20:30","Plaza de la Solidaridad","Finaos"),
    "details":"Celebración de Finaos con La Trova, Parranda Y Pa’ Cuándo y productos tradicionales. La reserva de mesa es opcional."}
  ]},
 {"municipality":"Vega de San Mateo",
  "url":"https://www.vegadesanmateo.es/noticia/se-abre-el-plazo-para-participar-en-el-iii-mercado-navideno-de-san-mateo",
  "events":[
   {"title":"III Mercado Navideño de Vega de San Mateo","date":"2026-11-27","time":"16:00",
    "venue":"Rambla de la Constitución y Calle Principal","category":"gastronomia",
    "tokens":("27, 28 y 29 de noviembre de 2026","viernes 27","16:00","20:00","Rambla de la Constitución","Calle Principal"),
    "details":"Mercado navideño en la Rambla de la Constitución y Calle Principal. Viernes de 16:00 a 20:00."},
   {"title":"III Mercado Navideño de Vega de San Mateo","date":"2026-11-28","time":"10:00",
    "venue":"Rambla de la Constitución y Calle Principal","category":"gastronomia",
    "tokens":("27, 28 y 29 de noviembre de 2026","sábado 28","10:00","20:00","Rambla de la Constitución","Calle Principal"),
    "details":"Mercado navideño. Sábado de 10:00 a 20:00."},
   {"title":"III Mercado Navideño de Vega de San Mateo","date":"2026-11-29","time":"10:00",
    "venue":"Rambla de la Constitución y Calle Principal","category":"gastronomia",
    "tokens":("27, 28 y 29 de noviembre de 2026","domingo 29","10:00","15:00","Rambla de la Constitución","Calle Principal"),
    "details":"Mercado navideño. Domingo de 10:00 a 15:00."}
  ]},
 {"municipality":"Santa María de Guía",
  "url":"https://santamariadeguia.es/guia-inicia-las-celebraciones-de-su-v-centenario-con-un-acto-que-une-historia-y-musica/",
  "events":[
   {"title":"Acto inaugural del V Centenario de Santa María de Guía","date":"2026-11-01","time":"20:30",
    "venue":"Frontis de la Iglesia de Santa María de Guía","category":"cultura",
    "tokens":("1 de noviembre","20:30","frontis de la Iglesia","V Centenario","Braulio"),
    "details":"Conmemoración del V Centenario de la ciudad con intervenciones históricas y actuación de Braulio."}
  ]},
 {"municipality":"Gáldar",
  "url":"https://www.galdar.es/el-centro-cultural-guaires-prepara-una-amplia-programacion-de-espectaculos-para-los-proximos-meses/",
  "events":[
   {"title":"Conversaciones con mi mente · Joaquín Caserza","date":"2026-11-07","time":"20:00",
    "venue":"Centro Cultural Guaires","category":"cultura",
    "tokens":("7 de noviembre","20.00","Joaquín Caserza","Conversaciones con mi mente","Centro Cultural Guaires"),
    "details":"Espectáculo de humor con Joaquín Caserza, dentro de la programación oficial del Centro Cultural Guaires."},
   {"title":"Todo pa' última hora · Jorge Ávila","date":"2026-11-14","time":"20:00",
    "venue":"Centro Cultural Guaires","category":"cultura",
    "tokens":("14 de noviembre","20.00","Jorge Ávila","Todo pa","Centro Cultural Guaires"),
    "details":"Stand-up de Jorge Ávila en el Centro Cultural Guaires."},
   {"title":"Solo Palique · humor en directo","date":"2026-11-20","time":"20:30",
    "venue":"Centro Cultural Guaires","category":"cultura",
    "tokens":("20 de noviembre","20.30","Solo Palique","Centro Cultural Guaires"),
    "details":"Espectáculo y podcast de humor improvisado en el Centro Cultural Guaires."},
   {"title":"Más allá del Pasillo · Iván Torres","date":"2026-11-28","time":"20:00",
    "venue":"Centro Cultural Guaires","category":"musica",
    "tokens":("28 de noviembre","20.00","Más allá del Pasillo","Iván Torres","Centro Cultural Guaires"),
    "details":"Propuesta escénica de Iván Torres, vocalista y compositor de Efecto Pasillo."}
  ]},
 {"municipality":"Valleseco",
  "url":"https://valleseco.es/valleseco/valleseco-acoge-wuateluz-la-nueva-exposicion-de-felipe-juan/",
  "events":[
   {"title":"WuateLuz · exposición de Felipe Juan","date":"2026-10-09",
    "end":"2026-10-31","time":None,
    "venue":"Sala de Exposiciones del Auditorio Dr. Juan Díaz Rodríguez","category":"cultura",
    "tokens":("WuateLuz","Felipe Juan","9 de octubre","31 de octubre de 2026",
              "Sala de Exposiciones","Auditorio"),
    "details":"Exposición de Felipe Juan abierta del 9 al 31 de octubre de 2026. El Ayuntamiento no confirma el horario diario en esta noticia; consulta la fuente antes de ir."}
  ]},
 {"municipality":"Santa Lucía de Tirajana",
  "url":"https://www.santaluciagc.com/abubukaka-pablo-carbonel-alex-ubago-maria-pelae-talleres-cine-magia-y-exposiciones-en-la-programacion-de-cultura/",
  "events":[
   {"title":"El último presidente","date":"2026-10-30","time":None,
    "venue":"Teatro Víctor Jara","category":"cultura",
    "tokens":("El último presidente","30 de octubre","teatro Víctor Jara"),
    "details":"Teatro municipal de Vecindario. Horario no publicado en esta noticia; consultar taquilla oficial."},
   {"title":"María Peláe","date":"2026-10-31","time":None,
    "venue":"Teatro Víctor Jara","category":"musica",
    "tokens":("El último presidente","30 de octubre","Al día siguiente","María Peláe"),
    "details":"Concierto anunciado para el día siguiente al 30 de octubre. Hora por verificar en la venta oficial."},
   {"title":"Género de dudas","date":"2026-11-20","time":None,
    "venue":"Teatro Víctor Jara","category":"cultura",
    "tokens":("20 de noviembre","Género de dudas","Pablo Carbonel","Pastora Vega"),
    "details":"Comedia interpretada por Pablo Carbonel y Pastora Vega. Hora por confirmar."},
   {"title":"Álex Ubago","date":"2026-12-13","time":None,
    "venue":"Teatro Víctor Jara","category":"musica",
    "tokens":("13 de diciembre","Alex Ubago","teatro Víctor Jara"),
    "details":"Concierto de Álex Ubago en Vecindario. Hora por confirmar en la taquilla."},
   {"title":"Festival Internacional de Magia · Víctor Jara","date":"2026-12-18","time":None,
    "venue":"Teatro Víctor Jara","category":"familia",
    "tokens":("18 de diciembre","Festival Internacional","Magia","teatro Víctor Jara"),
    "details":"Espectáculo del Festival Internacional de Magia. Horario por confirmar."},
   {"title":"En busca de la magia","date":"2026-12-23","time":None,
    "venue":"Teatro Víctor Jara","category":"familia",
    "tokens":("23 de diciembre","En busca de la magia","teatro Víctor Jara"),
    "details":"Teatro familiar. Horario de la función por confirmar."},
   {"title":"Bejeque Kids","date":"2026-12-26","time":None,
    "venue":"Teatro Víctor Jara","category":"familia",
    "tokens":("26 de diciembre","Bejeque Kids","teatro Víctor Jara"),
    "details":"Concierto infantil en el Teatro Víctor Jara. Hora por confirmar."}
  ]},
 {"municipality":"San Bartolomé de Tirajana",
  "url":"https://www.maspalomas.com/mnunotjuventud/3060-2026-ju-maspaterror-regresa-al-parque-sur-los-dias-30-y-31-de-octubre-presentando-su-tercera-edicion",
  "events":[
   {"title":"Casa del Terror de Maspaterror III","date":"2026-10-30","time":"18:00",
    "venue":"Parque Sur de Maspalomas","category":"familia",
    "tokens":("30","31 de octubre","Parque Sur","Casa del Terror","18:00","21:30"),
    "details":"Casa del Terror de Maspaterror III, de 18:00 a 21:30. Condiciones de acceso a confirmar con la organización."},
   {"title":"Casa del Terror de Maspaterror III","date":"2026-10-31","time":"18:00",
    "venue":"Parque Sur de Maspalomas","category":"familia",
    "tokens":("30","31 de octubre","Parque Sur","Casa del Terror","18:00","21:30"),
    "details":"Casa del Terror de Maspaterror III, de 18:00 a 21:30. Condiciones de acceso a confirmar con la organización."},
   {"title":"Concierto de Banda Sol y Arena · Maspaterror","date":"2026-10-30","time":"19:30",
    "venue":"Parque Sur de Maspalomas","category":"musica",
    "tokens":("viernes 30 de octubre","19:30","Banda Sol y Arena","Parque Sur"),
    "details":"Concierto dentro de la programación de Maspaterror III."},
   {"title":"Cuentos para temblar · Maspaterror","date":"2026-10-31","time":"17:30",
    "venue":"Parque Sur de Maspalomas","category":"familia",
    "tokens":("sábado 31 de octubre","Cuentos para temblar","17:30","Parque Sur"),
    "details":"Narración oral de Halloween dentro de Maspaterror III."},
   {"title":"Cine al aire libre: Casper · Maspaterror","date":"2026-10-31","time":"19:00",
    "venue":"Parque Sur de Maspalomas","category":"cultura",
    "tokens":("sábado 31 de octubre","19:00","Casper","Parque Sur"),
    "details":"Proyección de Casper al aire libre durante Maspaterror III."}
  ]}
)

def norm(value):
    t=unicodedata.normalize("NFKD",str(value or "").casefold())
    t="".join(char for char in t if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+"," ",t).strip()

def verify_article(entry,soup):
    # Full article text is published by the municipality. No page-level
    # inference from publication dates; individual scheduled times are curated.
    text=norm(soup.get_text(" ",strip=True))
    return "2026" in text and all(norm(x) in text for x in entry["tokens"])

def extract(get_html,today,municipalities,*,source_specs=SOURCES):
    rows=[]
    audit=[]
    for source in source_specs:
        name=source["municipality"]
        if name not in municipalities:
            continue
        eligible=[row for row in source["events"]
                  if today<=dt.date.fromisoformat(row.get("end") or row["date"])
                  and dt.date.fromisoformat(row["date"])<=today+dt.timedelta(days=120)]
        if not eligible:
            continue
        try:
            page=get_html(source["url"])
            found=0
            for item in eligible:
                if not verify_article(item,page):
                    audit.append({"municipality":name,"source_url":source["url"],
                                  "title":item["title"],"status":"unverified_text"})
                    continue
                rows.append({
                    "title":item["title"],
                    "start":(item["date"]+"T"+item["time"]+":00"
                             if item.get("time") else item["date"]),
                    "end":item.get("end"),
                    "municipality":name,
                    "venue":item["venue"],
                    "category":item["category"],
                    "free":None,"price":"",
                    "details":item["details"],
                    "source_name":"Ayuntamiento de "+name+" · actos documentados",
                    "source_url":source["url"],
                    "status":"approved"
                })
                found+=1
            audit.append({"municipality":name,"source_url":source["url"],
                          "checked":len(eligible),"verified":found,"status":"checked"})
        except Exception as exc:
            audit.append({"municipality":name,"source_url":source["url"],
                          "checked":len(eligible),"verified":0,
                          "status":"source_error","error_type":type(exc).__name__})
    return rows,audit
