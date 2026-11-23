"""Verified, non-sponsored public activities from shopping-centre organisers.

Official sources are not advertising. Never import shop offers, retail opening
hours or commercial promotions as events. Only dated, recognisable activities.
Las Arenas Club Arenillo has one official Christmas-season schedule; any
weekday/month inconsistency fails closed rather than inheriting a wrong year.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

from bs4 import BeautifulSoup

NAME = "Centro Comercial Las Arenas · Club Arenillo"
BASE = "https://cclasarenas.com/"
VENUE = "Centro Comercial Las Arenas"
TOWN = "Las Palmas de Gran Canaria"
WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}
MONTHS = {"noviembre": 11, "diciembre": 12, "enero": 1}
CLOCK = re.compile(r"\bde\s+(\d{1,2}:\d{2})\s+a\s+(\d{1,2}:\d{2})\b", re.I)
DAY_ACTIVITY = re.compile(r"^([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{1,2})\s+de\s+", re.I)
DAY_RANGE = re.compile(
    r"^Del\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{1,2})\s+al\s+"
    r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{1,2})$", re.I)
ARTICLE = re.compile(r"club arenillo.{0,80}navidad", re.I)
RETAIL_PROMO = re.compile(
    r"\b(?:rebajas|black friday|descuentos?|ofertas?|promociones?|"
    r"compra y gana|sorteo de compras|liquidaci[oó]n)\b", re.I)


def normalized(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def official_url(season):
    return BASE + f"club-arenillo-programacion-navidad-{season}/"


def season_for(today):
    # Do not keep recycling last Christmas's article in spring or summer.
    if today.month == 1:
        return today.year - 1 if today.day <= 10 else None
    if today.month in (10, 11, 12):
        return today.year
    return None


def dated(weekday, number, month, season):
    year = season + 1 if month == 1 else season
    try:
        stamp = dt.date(year, month, int(number))
    except ValueError:
        return None
    if WEEKDAYS.get(normalized(weekday)) != stamp.weekday():
        return None
    return stamp


def clock(value):
    try:
        t = dt.time.fromisoformat(value)
        return t.strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return None


def extract_las_arenas(soup, today, season):
    """Parse only the dated Club Arenillo programme, not sales or page banners.

    One card per day/activity; schedules with morning and afternoon slots keep
    both ranges in the description rather than inventing continuous opening.
    """
    if not isinstance(soup, BeautifulSoup):
        soup = BeautifulSoup(str(soup), "html.parser")
    article = soup.select_one("article")
    heading = article.select_one("h1") if article else None
    if not heading or not ARTICLE.search(normalized(heading.get_text(" ", strip=True))):
        return []
    # Explicit monthly programme, not an undated marketing article.
    text = article.get_text(" ", strip=True)
    if not all(m.upper() in text for m in ("NOVIEMBRE", "DICIEMBRE", "ENERO")):
        return []
    month, train = None, False
    november_blocks = False
    november_hours = []
    results, seen = [], set()
    source = official_url(season)
    until = dt.date(season + 1, 1, 10)

    def publish(title, stamp, periods, location):
        if not (today <= stamp <= until and periods and
                title and len(title) >= 7) or RETAIL_PROMO.search(title):
            # Store discounts are not cultural or family plans.
            return
        slots = [(clock(a), clock(b)) for a, b in periods]
        if any(not a or not b or b <= a for a, b in slots):
            return
        key = (normalized(title), stamp.isoformat())
        if key in seen:
            return
        seen.add(key)
        displayed = ", ".join(a[:5] + "–" + b[:5] for a, b in slots)
        details = (
            f"Actividad navideña de Club Arenillo para público infantil y familiar: "
            f"{title}, el {stamp.strftime('%d/%m/%Y')}, en {VENUE} "
            f"({location}). Horario anunciado: {displayed} h. "
            "Consulta la programación oficial del centro para conocer "
            "las condiciones y cualquier cambio de horario."
        )
        results.append({
            "title": title, "start": stamp.isoformat() + "T" + slots[0][0],
            "end": stamp.isoformat() + "T" + slots[-1][1],
            "municipality": TOWN, "venue": VENUE, "category": "familia",
            "free": None, "price": "", "details": details,
            "source_name": NAME, "source_url": source,
            "organizer_url": "", "status": "approved",
        })

    for tag in article.find_all(["p", "li"]):
        txt = " ".join(tag.get_text(" ", strip=True).split())
        key = normalized(txt).strip(":")
        if tag.name == "p":
            if "tren de renos del polo norte" in key:
                train = True
                month = None
            elif key in MONTHS:
                month = MONTHS[key]
            elif month == 11 and "taller de bloques de construccion" in key:
                november_blocks = True
                november_hours = CLOCK.findall(txt) or november_hours
            elif month == 11 and november_blocks and "horario" in key:
                november_hours = CLOCK.findall(txt)
            continue
        if not month:
            continue
        if train:
            hit = DAY_RANGE.fullmatch(txt)
            if not hit:
                continue
            start = dated(hit[1], hit[2], month, season)
            end = dated(hit[3], hit[4], month, season)
            if not start or not end or start > end or (end-start).days > 10:
                continue
            for n in range((end-start).days + 1):
                publish("Tren de renos del Polo Norte en Las Arenas",
                        start + dt.timedelta(days=n),
                        [("17:00", "20:00")],
                        "planta baja, junto a Vans")
            continue
        # November lists the dates separately from the official 17:00-20:00
        # heading; do not infer times from unrelated December paragraphs.
        if month == 11 and november_blocks and november_hours:
            only_date = re.fullmatch(
                r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{1,2})", txt)
            if only_date:
                stamp = dated(only_date[1], only_date[2], month, season)
                if stamp:
                    publish("Taller de bloques de construcción · Navidad en Las Arenas",
                            stamp, november_hours,
                            "planta baja, Doble Mall, frente a Stradivarius")
                continue
        hit = DAY_ACTIVITY.match(txt)
        if not hit:
            continue
        stamp = dated(hit[1], hit[2], month, season)
        if not stamp:
            continue
        periods = CLOCK.findall(txt)
        if not periods:
            continue
        # Activity must appear *after* the printed last time range.
        tail = txt[txt.rfind(periods[-1][1]) + len(periods[-1][1]):]
        match = re.search(r"[–—-]\s*(.*)$", tail)
        if not match:
            continue
        title = re.sub(r"^[^A-Za-zÁÉÍÓÚáéíóúñÑ0-9]+", "", match[1]).strip()
        if not title:
            continue
        publish(f"{title} · Navidad en Las Arenas", stamp, periods,
                "planta baja, Doble Mall, frente a Stradivarius")
    return results


def synchronize(conn, now, today, upsert, fetch_html):
    """A single daily, robots-aware request with error isolation and audit."""
    season = season_for(today)
    found = added = changed = 0
    error = ""
    if season is not None:
        try:
            entries = extract_las_arenas(fetch_html(official_url(season)), today, season)
            if not entries:
                raise ValueError("No verified upcoming sessions; review official dates")
            for entry in entries:
                result = upsert(conn, entry)
                found += 1
                added += int(result == "added")
                changed += int(result == "changed")
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:160]
    conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
        VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
        checked_at=excluded.checked_at,found=excluded.found,
        added=excluded.added,changed=excluded.changed,error=excluded.error""",
        (NAME, str(now), found, added, changed, error))
    conn.commit()
    return {"source": NAME, "checked_at": str(now), "found": found,
            "added": added, "changed": changed, "error": error,
            "official_url": official_url(season) if season else ""}


ECI_NAME = "El Corte Inglés Mesa y López · Mercado de Navidad"
ECI_URL = (
    "https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/"
    "eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/mercado-navideno-las-palmas"
)


def extract_eci_market(soup, today, season):
    """Official, dated Christmas market, not individual products or promotions."""
    if not isinstance(soup, BeautifulSoup):
        soup = BeautifulSoup(str(soup), "html.parser")
    headings = [normalized(h.get_text(" ", strip=True)) for h in soup.select("h1")]
    if "mercado navideno las palmas" not in headings:
        return []
    text = " ".join(soup.get_text(" ", strip=True).split())
    actual_dates = re.compile(
        rf"\b20 de noviembre de {season}\s+al\s+5 de enero de {season+1}\b", re.I)
    if not actual_dates.search(text):
        return []
    if not re.search(r"\bAcceso:\s*Libre\b", text, re.I):
        return []
    if not re.search(r"\b12:00\s*-\s*23:00\b", text):
        return []
    if "José Mesa y López, 18" not in text:
        return []
    if today > dt.date(season+1, 1, 5):
        return []
    return [{
        "title": "Mercado Navideño Las Palmas · Mesa y López",
        "start": f"{season}-11-20T12:00:00",
        "end": f"{season+1}-01-05T23:00:00",
        "municipality": TOWN, "venue": "El Corte Inglés José Mesa y López",
        "category": "gastronomia", "free": 1, "price": "Acceso libre",
        "details": (
            "Mercado de Navidad de El Corte Inglés en la avenida José Mesa y López, "
            "con casetas de artesanía, regalos, decoración, cultura y gastronomía. "
            "Acceso libre, del 20 de noviembre al 5 de enero; el horario habitual "
            "de restauración es de 12:00 a 23:00 h y las casetas de 12:00 a 21:30 h. "
            "Cierra el 25 de diciembre y el 1 de enero; los días 24 y 31 de diciembre "
            "abre de 12:00 a 20:00 h. Los productos y consumiciones son de pago."
        ),
        "source_name": ECI_NAME, "source_url": ECI_URL,
        "organizer_url": "", "status": "approved",
    }]


def synchronize_eci(conn, now, today, upsert, fetch_html):
    """Independent source log; one blocked centre cannot cancel another."""
    season = season_for(today)
    found = added = changed = 0
    error = ""
    if season is not None:
        try:
            entries = extract_eci_market(fetch_html(ECI_URL), today, season)
            if not entries:
                raise ValueError("No current, dated official market programme")
            for entry in entries:
                outcome = upsert(conn, entry)
                found += 1
                added += int(outcome == "added")
                changed += int(outcome == "changed")
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:160]
    conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
        VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
        checked_at=excluded.checked_at,found=excluded.found,
        added=excluded.added,changed=excluded.changed,error=excluded.error""",
        (ECI_NAME, str(now), found, added, changed, error))
    conn.commit()
    return {"source": ECI_NAME, "checked_at": str(now), "found": found,
            "added": added, "changed": changed, "error": error,
            "official_url": ECI_URL if season else ""}
