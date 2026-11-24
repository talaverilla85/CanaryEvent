"""Mogán Mall 2026–27: dated sessions verified against the official public PDF.

The organiser's website links to this official one-page, image-only PDF.
The website returns HTTP 403 to the named event bot, so do not bypass the block
or pretend to scrape Elementor HTML. The 2026 calendar is a carefully verified
seasonal snapshot, transcribed from the organiser's PDF, not a live PDF parser.
Future seasons require a separately verified official programme/source.

No photos or source files are downloaded TO Google Drive. A Google-hosted
thumbnail of the organiser's *own public PDF* is linked as the programme image.
"""
from __future__ import annotations
import datetime as dt

NAME = "Centro Comercial Mogán Mall · Agenda de Navidad 2026"
VENUE = "Centro Comercial Mogán Mall"
MUNICIPALITY = "Mogán"
OFFICIAL_PAGE = "https://moganmall.com/navidad/"
OFFICIAL_PDF = (
    "https://drive.google.com/file/d/"
    "1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v/view"
)
OFFICIAL_PDF_FILE_ID = "1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v"
OFFICIAL_IMAGE = (
    "https://drive.google.com/thumbnail?"
    "id=1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v&sz=w640"
)
SEASON_START = dt.date(2026, 11, 14)
SEASON_END = dt.date(2027, 1, 6)

# (official calendar day, verified starting time, optional end clock/ISO,
#  activity name, editorial category). No dates or prices are inferred.
# Commercial gift-card/"Magic Ticket" promotions are intentionally excluded.
PROGRAMME = [
  [
    "2026-11-14",
    "18:00",
    "",
    "Encendido de Navidad con show navideño",
    "familia"
  ],
  [
    "2026-11-20",
    "18:00",
    "",
    "Ballet ruso inspirado en La Bella Durmiente",
    "cultura"
  ],
  [
    "2026-11-20",
    "19:00",
    "",
    "Cuentacuentos de Navidad",
    "familia"
  ],
  [
    "2026-11-21",
    "10:00",
    "21:00",
    "Mercado del Coleccionismo",
    "ocio"
  ],
  [
    "2026-11-21",
    "18:00",
    "",
    "Nevada navideña",
    "familia"
  ],
  [
    "2026-11-21",
    "18:30",
    "",
    "Musical Érase una vez",
    "cultura"
  ],
  [
    "2026-11-22",
    "10:00",
    "21:00",
    "Mercado del Coleccionismo",
    "ocio"
  ],
  [
    "2026-11-27",
    "16:30",
    "19:30",
    "Castillo hinchable con Don Sonrisas",
    "familia"
  ],
  [
    "2026-11-28",
    "18:00",
    "",
    "Jurassic Garden",
    "familia"
  ],
  [
    "2026-11-29",
    "12:00",
    "",
    "Jurassic Garden",
    "familia"
  ],
  [
    "2026-12-04",
    "16:30",
    "19:30",
    "Castillo hinchable con Don Sonrisas",
    "familia"
  ],
  [
    "2026-12-04",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-05",
    "17:00",
    "20:00",
    "Acción solidaria Un cuento de Navidad",
    "familia"
  ],
  [
    "2026-12-05",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-05",
    "18:00",
    "",
    "Nevada mágica",
    "familia"
  ],
  [
    "2026-12-05",
    "19:00",
    "",
    "Mundo mágico con la maga Miriam Santana",
    "familia"
  ],
  [
    "2026-12-06",
    "17:00",
    "20:00",
    "Acción solidaria Un cuento de Navidad",
    "familia"
  ],
  [
    "2026-12-07",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-11",
    "19:00",
    "",
    "Cuentacuentos de Navidad",
    "familia"
  ],
  [
    "2026-12-12",
    "10:00",
    "21:00",
    "Mercado del Coleccionismo",
    "ocio"
  ],
  [
    "2026-12-12",
    "18:00",
    "",
    "Nevada navideña",
    "familia"
  ],
  [
    "2026-12-12",
    "19:00",
    "",
    "Concierto de la banda sinfónica Real Ciudad de Gáldar",
    "musica"
  ],
  [
    "2026-12-13",
    "10:00",
    "21:00",
    "Mercado del Coleccionismo",
    "ocio"
  ],
  [
    "2026-12-18",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-18",
    "18:00",
    "",
    "Actuación del colegio Canterbury de Maspalomas",
    "musica"
  ],
  [
    "2026-12-19",
    "18:00",
    "",
    "Ballet ruso inspirado en La Bella Durmiente",
    "cultura"
  ],
  [
    "2026-12-19",
    "19:00",
    "",
    "Concierto The Royal Voice",
    "musica"
  ],
  [
    "2026-12-20",
    "18:00",
    "",
    "Actuación musical del British School de Maspalomas",
    "musica"
  ],
  [
    "2026-12-20",
    "19:00",
    "",
    "Concierto familiar Gran Canaria Brass Connection",
    "musica"
  ],
  [
    "2026-12-21",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-22",
    "12:00",
    "2027-01-06T20:00:00",
    "Pista de hielo sintético de Navidad",
    "familia"
  ],
  [
    "2026-12-22",
    "18:00",
    "",
    "Visita de personajes navideños por el centro",
    "familia"
  ],
  [
    "2026-12-22",
    "18:00",
    "",
    "Taller familiar Guatduwidu",
    "familia"
  ],
  [
    "2026-12-23",
    "17:30",
    "",
    "Gran visita de Papá Noel con nevada navideña",
    "familia"
  ],
  [
    "2026-12-26",
    "18:00",
    "",
    "Nevada navideña",
    "familia"
  ],
  [
    "2026-12-26",
    "18:30",
    "",
    "Show de magia inspirado en Harry Potter",
    "familia"
  ],
  [
    "2026-12-27",
    "12:00",
    "20:00",
    "Pasaporte Guatduwidu",
    "familia"
  ],
  [
    "2026-12-28",
    "12:00",
    "20:00",
    "Pasaporte Guatduwidu",
    "familia"
  ],
  [
    "2026-12-30",
    "18:30",
    "",
    "Coro góspel de Navidad",
    "musica"
  ],
  [
    "2027-01-02",
    "12:00",
    "",
    "Cabalgata de personajes de fantasía",
    "familia"
  ],
  [
    "2027-01-04",
    "17:30",
    "",
    "Gran visita de los Reyes Magos de Oriente",
    "familia"
  ]
]

def _build(title, day, start, end, category):
    stamp = dt.date.fromisoformat(day)
    if not SEASON_START <= stamp <= SEASON_END:
        raise ValueError("Event outside the verified 2026 programme")
    begins = dt.datetime.fromisoformat(day + "T" + start + ":00")
    finish = None
    if end:
        finish_text = (end if "T" in end else day + "T" + end + ":00")
        finish = dt.datetime.fromisoformat(finish_text)
        if finish <= begins:
            raise ValueError("Event end is before start")
    final_day = finish.date() if finish else stamp
    display_end = (" hasta el " + finish.strftime("%d/%m/%Y a las %H:%M")
                   if finish and finish.date() != stamp else
                   (", hasta las " + finish.strftime("%H:%M") if finish else ""))
    duration = ("Abierta de 12:00 a 20:00 h durante el periodo anunciado. "
                if title == "Pista de hielo sintético de Navidad" else "")
    details = (
        f"{title}. Actividad incluida en la agenda oficial de Navidad 2026 "
        f"de Mogán Mall, en avenida Tomás Roca Bosch, 9, Puerto Rico, Mogán "
        f"(Gran Canaria). Fecha: {stamp.strftime('%d/%m/%Y')} a las {start}"
        f"{display_end} h. {duration}"
        "Consulta el programa original del organizador para condiciones, "
        "posibles cambios de horario y requisitos de acceso."
    )
    return {
        "title": title + " · Navidad en Mogán Mall",
        "start": begins.isoformat(timespec="seconds"),
        "end": finish.isoformat(timespec="seconds") if finish else None,
        "municipality": MUNICIPALITY,
        "venue": VENUE,
        "category": category,
        "free": None,
        "price": "",
        "details": details,
        "source_name": NAME,
        "source_url": OFFICIAL_PDF,
        "organizer_url": OFFICIAL_PAGE,
        "status": "approved",
        "image_url": OFFICIAL_IMAGE,
        "image_alt": "Imagen oficial de la agenda navideña 2026 de Mogán Mall",
        "image_origin": OFFICIAL_PDF,
        "image_status": "official_remote",
    }


def _fountain_rows():
    # The poster explicitly says: all Fridays and Saturdays, 20:00,
    # from 4 Dec 2026 through 2 Jan 2027. One entry per actual session.
    day = dt.date(2026, 12, 4)
    last = dt.date(2027, 1, 2)
    while day <= last:
        if day.weekday() in (4, 5):
            yield (day.isoformat(), "20:00", "",
                   "Show de la fuente especial de Navidad", "familia")
        day += dt.timedelta(days=1)


def verified_entries(today):
    """Return current/future official 2026–27 sessions only.

    Since the PDF is a raster image, it has no machine-readable event text.
    This explicit transcription is deliberately scoped to this season.
    """
    if not isinstance(today, dt.date):
        raise TypeError("A date is required")
    if not SEASON_START <= today <= SEASON_END:
        return []
    result, seen = [], set()
    for day, start, end, title, category in list(PROGRAMME) + list(_fountain_rows()):
        # Do not repeat fully expired events, and never fabricate future seasons.
        last_day = dt.date.fromisoformat(end[:10]) if "T" in end else dt.date.fromisoformat(day)
        if last_day < today:
            continue
        item = _build(title, day, start, end, category)
        key = (item["title"], item["start"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (item["start"], item["title"]))


def synchronize(conn, now, today, upsert):
    """Use official transcribed dates; log this source independently.

    No network requests to the blocked organiser website. On a different
    season, the connector stays dormant until another PDF is reviewed.
    """
    found = added = changed = 0
    error = ""
    try:
        for item in verified_entries(today):
            action = upsert(conn, item)
            found += 1
            added += int(action == "added")
            changed += int(action == "changed")
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)[:180]
    conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
        VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
        checked_at=excluded.checked_at,found=excluded.found,
        added=excluded.added,changed=excluded.changed,error=excluded.error""",
        (NAME, str(now), found, added, changed, error))
    conn.commit()
    return {"source": NAME, "checked_at": str(now), "found": found,
            "added": added, "changed": changed, "error": error,
            "official_url": OFFICIAL_PDF, "mode": "verified_pdf_2026_snapshot"}
