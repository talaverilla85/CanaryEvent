"""Facts sourced from the official Santa Lucia de Tirajana 2026 festivities notices.

This adapter is intentionally event/program-specific. It is NOT a generic
natural-language scraper: only explicitly dated items documented by the
municipal organizer are published. Other years require a new program review.
"""
import datetime as dt
from bs4 import BeautifulSoup

NAME="Ayuntamiento de Santa Lucía · Fiestas de San Rafael"
MUNICIPALITY="Santa Lucía de Tirajana"
PROGRAM="https://www.santaluciagc.com/fiestas-san-rafael-2026/"
ANNOUNCEMENT="https://www.santaluciagc.com/braulio-los-gofiones-bejeque-los-coquillos-enac-ska-cristina-ramos-antonia-san-juan-y-matias-alonso-en-las-fiestas-de-san-rafael/"
BRAULIO="https://www.santaluciagc.com/el-cantante-braulio-dara-un-concierto-el-25-de-octubre-en-las-fiestas-de-san-rafael-de-vecindario/"

# All schedule claims must be individually supported by the municipal news.
FESTIVAL_ITEMS=(
 # title, start, end, venue, free, details, evidence_tokens
 ("Fiestas de San Rafael 2026 · Vecindario","2026-10-16","2026-11-01",
  "Consultar el recinto en la ficha oficial",
  None,"Programación de fiestas patronales en Vecindario, del 16 de octubre al 1 de noviembre. Consulta días y actos concretos en el programa municipal.",
  ("fiestas de san rafael","16 de octubre","1 de noviembre")),
 ("Concierto de Braulio · San Rafael","2026-10-25T20:00:00",None,
  "Recinto Ferial de Vecindario",None,"Concierto del cantante Braulio durante las fiestas de San Rafael.",
  ("domingo 25","20 horas","recinto ferial","braulio")),
 ("Actividades infantiles · San Rafael","2026-10-26",None,
  "Consultar el recinto en la ficha oficial",None,"Actividades infantiles de las fiestas de San Rafael. Consulta el programa del Ayuntamiento para el horario y lugar exactos.",
  ("lunes 26","actividades infantiles")),
 ("Noche de Tapas · San Rafael","2026-10-29",None,
  "Consultar el recinto en la ficha oficial",None,"Noche de Tapas dentro de las fiestas de San Rafael. Consulta el programa para el horario y escenario exactos.",
  ("jueves 29","noche de tapas")),
 ("Tenderete de Vecindario · San Rafael","2026-10-30T20:00:00",None,
  "Consultar el recinto en la ficha oficial",None,"Actuaciones de agrupaciones folclóricas durante las fiestas de San Rafael.",
  ("viernes 30","20 horas","tendere")),
 ("Concierto de Los Coquillos · San Rafael","2026-10-30T22:00:00",None,
  "Consultar el recinto en la ficha oficial",None,"Concierto de Los Coquillos por su gira 35 aniversario en las fiestas de San Rafael.",
  ("22 horas","los coquillos")),
 ("Fin de fiestas · Shaila Dúrcal","2026-11-01",None,
  "Consultar el recinto en la ficha oficial",None,"Actuación de Shaila Dúrcal en el final de las fiestas de San Rafael. Consulta el programa para el horario concreto.",
  ("domingo","shaila durcal")),
)

def extract(announcement_html,braulio_html,today,normalized,categorize,municipalities):
    if MUNICIPALITY not in municipalities:return []
    if today>dt.date(2026,11,1) or today<dt.date(2026,9,1):return []
    announcement=normalized(BeautifulSoup(announcement_html,"html.parser").get_text(" ",strip=True))
    braulio=normalized(BeautifulSoup(braulio_html,"html.parser").get_text(" ",strip=True))
    if not all(normalized(t) in announcement for t in ("San Rafael","2026","16 de octubre","1 de noviembre")):
        raise ValueError("Official Santa Lucia festivities article missing expected dates")
    entries=[]
    for title,start,end,venue,free,details,tokens in FESTIVAL_ITEMS:
        text=announcement
        if not all(normalized(tok) in text for tok in tokens):
            raise ValueError(f"Official source does not verify: {title}")
        finish=(end or start)[:10]
        if finish<today.isoformat():continue
        is_braulio="Braulio" in title
        if is_braulio and normalized("concierto gratuito") not in braulio:
            raise ValueError("Official Braulio announcement does not explicitly confirm free entry")
        entries.append(dict(
            title=title,start=start,end=end,municipality=MUNICIPALITY,venue=venue,
            category=categorize(title),free=1 if is_braulio else None,
            price="Gratis" if is_braulio else "",
            details=details,source_name=NAME,source_url=BRAULIO if is_braulio else
                    PROGRAM if "Fiestas de San Rafael 2026" in title else ANNOUNCEMENT,
            status="approved"))
    return entries

