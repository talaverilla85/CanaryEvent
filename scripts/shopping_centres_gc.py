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
from urllib.parse import urljoin, urlsplit

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


def official_image(soup, host, required_path, match_alt="mercado navideno las palmas"):
    """Only a source page's own HTTPS campaign photo, never unrelated banners.

    Reusing a genuine season-wide banner is explicitly described as a
    programme image, not falsely as a photograph of each individual workshop.
    """
    if host == "cclasarenas.com":
        tag = soup.select_one('meta[property="og:image"][content]')
        candidate = tag.get("content", "") if tag else ""
    elif host == "www.centroscomerciales.elcorteingles.es":
        tag = next((el for el in soup.select('img[alt][src]')
                    if normalized(el.get("alt")) == match_alt), None)
        candidate = tag.get("src", "") if tag else ""
    else:
        return ""
    try:
        parsed = urlsplit(candidate)
        if (parsed.scheme == "https" and parsed.hostname == host and
                parsed.path.startswith(required_path) and
                re.search(r"\.(?:jpe?g|png|webp)$", parsed.path, re.I)):
            return candidate
    except ValueError:
        pass
    return ""


def extract_las_arenas(soup, today, season):
    """Parse only the dated Club Arenillo programme, not sales or page banners.

    One card per day/activity. Morning and afternoon sessions of the
    same workshop remain inside one record with both schedules stated; never
    infer that the activity runs through the intervening break.
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
    programme_image = official_image(soup, "cclasarenas.com",
                                   f"/wp-content/uploads/{season}/")
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
            "image_url": programme_image,
            "image_alt": "Imagen oficial del programa navideño de Las Arenas" if programme_image else "",
            "image_origin": source if programme_image else "",
            "image_status": "official_remote" if programme_image else "",
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
    market_image = official_image(
        soup, "www.centroscomerciales.elcorteingles.es",
        "/centroscomerciales/uploads/events/")
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
        "image_url": market_image,
        "image_alt": "Imagen oficial del Mercado Navideño Las Palmas" if market_image else "",
        "image_origin": ECI_URL if market_image else "",
        "image_status": "official_remote" if market_image else "",
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


ECI_SHOWS_NAME = "El Corte Inglés Mesa y López · Espectáculos de Navidad"
ECI_SHOWS_URL = (
    "https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/"
    "eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/"
    "una-navidad-llena-de-magia-risas-y-diversion-para-toda-la-familia"
)
ECI_SHOWS_TITLE = "una navidad llena de magia, risas y diversion para toda la familia"
ECI_SHOW_PATTERN = re.compile(
    r"\b(lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s*,?\s*"
    r"(\d{1,2})\s+de\s+diciembre\s*:\s*(.+)$", re.I,
)


def extract_eci_shows(soup, today, season, verified_market=False):
    """One card per dated show, only after 2026 market validates the season.

    The shows article has dates and weekdays but NO year. The independently
    confirmed companion market programme anchors the season; each weekday
    must then agree with the actual calendar year. No auto-guessing a year
    from a December-only undated programme.
    """
    if not verified_market or season is None:
        return []
    if not isinstance(soup, BeautifulSoup):
        soup = BeautifulSoup(str(soup), "html.parser")
    headings = [normalized(h.get_text(" ", strip=True))
                for h in soup.select("h1")]
    if not any(h.startswith('una navidad llena de magia') and 'toda la familia' in h for h in headings):
        return []
    text = " ".join(soup.get_text(" ", strip=True).split())
    if not all(value in normalized(text) for value in (
        "programacion de diciembre", "acceso: libre",
        "del 4 de diciembre al 30 de diciembre",
        "horario: 18:00 - 19:00",
    )):
        return []
    image = official_image(
        soup, "www.centroscomerciales.elcorteingles.es",
        "/centroscomerciales/uploads/events/", ECI_SHOWS_TITLE)
    result, seen = [], set()
    for li in soup.select("li"):
        label = " ".join(li.get_text(" ", strip=True).split())
        match = ECI_SHOW_PATTERN.search(label)
        if not match:
            continue
        stamp = dated(match[1], match[2], 12, season)
        if not stamp or not (dt.date(season, 12, 4) <= stamp <=
                             dt.date(season, 12, 30)):
            continue
        raw_title = re.sub(r"[.!?]+$", "", match[3]).strip()
        if not raw_title or len(raw_title) < 5 or len(raw_title) > 85:
            continue
        key = (stamp, normalized(raw_title))
        if key in seen or stamp < today:
            continue
        seen.add(key)
        category = "musica" if "coros" in normalized(raw_title) else "familia"
        title = f"{raw_title} · Navidad en Mesa y López"
        detail = (
            f"{raw_title}, actividad de la programación navideña familiar "
            f"en el Mercado de Navidad de El Corte Inglés José Mesa y López, "
            f"Las Palmas de Gran Canaria. Día {stamp.strftime('%d/%m/%Y')}, "
            "de 18:00 a 19:00 h. Entrada libre según el programa oficial. "
            "Consulta el enlace de la organización por posibles cambios."
        )
        result.append({
            "title": title, "start": stamp.isoformat() + "T18:00:00",
            "end": stamp.isoformat() + "T19:00:00",
            "municipality": TOWN, "venue": "El Corte Inglés José Mesa y López",
            "category": category, "free": 1, "price": "Entrada libre",
            "details": detail, "source_name": ECI_SHOWS_NAME,
            "source_url": ECI_SHOWS_URL, "organizer_url": "",
            "status": "approved",
            "image_url": image,
            "image_alt": "Imagen oficial del programa de espectáculos familiares de Navidad"
                         if image else "",
            "image_origin": ECI_SHOWS_URL if image else "",
            "image_status": "official_remote" if image else "",
        })
    return result


def synchronize_eci_shows(conn, now, today, upsert, fetch_html):
    """Separate failure log. Verify the companion market's explicit year."""
    season = season_for(today)
    found = added = changed = 0
    error = ""
    if season is not None and today <= dt.date(season, 12, 30):
        try:
            market = extract_eci_market(
                fetch_html(ECI_URL), today, season)
            if not market:
                raise ValueError("Cannot verify December programme season")
            events = extract_eci_shows(
                fetch_html(ECI_SHOWS_URL), today, season,
                verified_market=True)
            if not events:
                raise ValueError("No dated future performances verified")
            for event in events:
                outcome = upsert(conn, event)
                found += 1
                added += int(outcome == "added")
                changed += int(outcome == "changed")
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:160]
    conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
        VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
        checked_at=excluded.checked_at,found=excluded.found,
        added=excluded.added,changed=excluded.changed,error=excluded.error""",
        (ECI_SHOWS_NAME, str(now), found, added, changed, error))
    conn.commit()
    return {"source": ECI_SHOWS_NAME, "checked_at": str(now),
            "found": found, "added": added, "changed": changed,
            "error": error,
            "official_url": ECI_SHOWS_URL if season else ""}


# Siete Palmas is a news feed, not an event calendar: publish only specific,
# future activities with an actual date AND advertised starting time. Its
# promotional articles, old celebrations and undated Christmas campaigns are
# never individual events. We link the official event image without copying.
SP_NAME = "Centro Comercial Siete Palmas · agenda oficial"
SP_URL = "https://sietepalmascc.com/ahora-mas/eventos"
SP_VENUE = "Centro Comercial Siete Palmas"
SP_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
SP_DATE = re.compile(
    r"\b(?:(?P<weekday>lunes|martes|miércoles|miercoles|jueves|viernes|"
    r"sábado|sabado|domingo)\s*,?\s+)?(?:el\s+)?"
    r"(?P<day>\d{1,2})\s+de\s+"
    r"(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+(?P<year>20\d{2}))?\b", re.I)
SP_TIME_RANGE = re.compile(
    r"\b(?:de|desde las)\s+(\d{1,2}:\d{2})\s*(?:a|hasta las|[-–])\s*"
    r"(\d{1,2}:\d{2})\b", re.I)
SP_START_TIME = re.compile(r"\b(?:a las|desde las)\s+(\d{1,2}:\d{2})\b", re.I)
SP_RETAIL = re.compile(
    r"\b(?:rebajas|black friday|descuentos?|promociones?|ofertas?|"
    r"liquidación|liquidacion|reabre sus puertas|apertura de tienda|"
    r"inauguraci[oó]n de tienda|nueva colección|nueva coleccion)\b", re.I)
SP_ACTIVITY = re.compile(
    r"\b(?:taller(?:es)?|festival|música|musica|concierto|magia|"
    r"papá noel|papa noel|navidad|encendido|espectáculo|espectaculo|"
    r"cuentacuentos|teatro|recogida de juguetes|animación|animacion|"
    r"infantil|familiar|juegos|lego|actuación|actuacion)\b", re.I)


def siete_palmas_links(soup):
    """Recent same-origin official articles only, never external links."""
    if not isinstance(soup, BeautifulSoup):
        soup = BeautifulSoup(str(soup), "html.parser")
    main = soup.select_one("main") or soup
    found = []
    for a in main.select("a[href]"):
        url = urljoin(SP_URL + "/", a.get("href", ""))
        p = urlsplit(url)
        if (p.scheme != "https" or p.netloc != "sietepalmascc.com" or
                not re.fullmatch(r"/ahora-mas/eventos/[a-z0-9-]+/?", p.path)):
            continue
        canonical = "https://sietepalmascc.com" + p.path.rstrip("/")
        if canonical not in found:
            found.append(canonical)
    return found


def siete_palmas_published(soup):
    """Use the official article date ONLY to disambiguate its own near-future
    yearless dates; never publish the article date as an event by itself."""
    for node in soup.select("meta[property='article:published_time'][content],"
                            " time[datetime]"):
        value = node.get("content") or node.get("datetime") or ""
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            pass
    text = soup.get_text(" ", strip=True)
    m = re.search(r"\bFecha\s+(\d{1,2})\s+de\s+"
                  r"([A-Za-zÁÉÍÓÚÜáéíóúü]+)\s+(20\d{2})\b", text, re.I)
    if not m:
        return None
    try:
        return dt.date(int(m[3]), SP_MONTHS[normalized(m[2])], int(m[1]))
    except (ValueError, KeyError):
        return None



def siete_palmas_official_image(soup):
    """Reference official article images by URL, without downloading them."""
    for selector, attribute in (
        ('meta[property="og:image"][content]', "content"),
        ('meta[name="twitter:image"][content]', "content"),
        ("main article img[src]", "src"),
        ("main picture img[src]", "src"),
        ("main img[src]", "src"),
    ):
        for node in soup.select(selector):
            candidate = node.get(attribute, "")
            if not candidate:
                continue
            url = urljoin("https://sietepalmascc.com/", str(candidate).strip())
            try:
                parsed = urlsplit(url)
                if (parsed.scheme != "https" or not parsed.hostname or
                        parsed.username or parsed.password or
                        parsed.port not in (None, 443)):
                    continue
            except ValueError:
                continue
            host = parsed.hostname.lower()
            if (host in ("localhost", "127.0.0.1", "::1") or
                    host.endswith((".local", ".internal")) or
                    re.fullmatch(r"\d+(?:\.\d+){3}", host)):
                continue
            pathname = parsed.path.lower()
            if (not re.search(r"\.(?:jpe?g|png|webp|avif)$", pathname) or
                    re.search(r"(?:^|[/_-])(?:logo|favicon|avatar|placeholder|icon)(?:[/_.-]|$)", pathname)):
                continue
            return url
    return ""


def extract_siete_palmas_article(soup, source_url, today):
    """Return a verified dated event or None (no guesswork on stale stories)."""
    if not isinstance(soup, BeautifulSoup):
        soup = BeautifulSoup(str(soup), "html.parser")
    url = urlsplit(source_url)
    if (url.scheme != "https" or url.netloc != "sietepalmascc.com" or
            not re.fullmatch(r"/ahora-mas/eventos/[a-z0-9-]+/?", url.path)):
        return None
    main = soup.select_one("main") or soup
    heading = main.select_one("h1")
    if not heading:
        return None
    title = " ".join(heading.get_text(" ", strip=True).split())[:160]
    if not title or SP_RETAIL.search(title) or not SP_ACTIVITY.search(title):
        return None
    published = siete_palmas_published(soup)
    for tag in main.select("p"):
        sentence = " ".join(tag.get_text(" ", strip=True).split())
        dates = list(SP_DATE.finditer(sentence))
        if len(dates) != 1:
            continue  # no ambiguous multi-day schedules
        match = dates[0]
        time_range = SP_TIME_RANGE.search(sentence)
        time_start = SP_START_TIME.search(sentence) if not time_range else None
        if not (time_range or time_start):
            continue
        try:
            month = SP_MONTHS[normalized(match["month"])]
            year = int(match["year"]) if match["year"] else (published.year if published else None)
            if year is None:
                continue
            stamp = dt.date(year, month, int(match["day"]))
            # A yearless date is valid only close to its dated publication.
            if not match["year"] and not (
                    published <= stamp <= published + dt.timedelta(days=60)):
                continue
            weekday = match["weekday"]
            if weekday and WEEKDAYS.get(normalized(weekday)) != stamp.weekday():
                continue
            if not today <= stamp <= today + dt.timedelta(days=180):
                continue
            start_value = (time_range or time_start)[1]
            start = dt.time.fromisoformat(start_value)
            end = dt.time.fromisoformat(time_range[2]) if time_range else None
            if end is not None and end <= start:
                continue
        except (TypeError, ValueError, KeyError):
            continue
        info = (f"{title}. Actividad anunciada para el "
                f"{stamp.strftime('%d/%m/%Y')} a las {start.strftime('%H:%M')} h"
                + (f", hasta las {end.strftime('%H:%M')} h" if end else "")
                + f" en {SP_VENUE}. Consulta la fuente oficial antes de acudir.")
        price_known_free = bool(re.search(
            r"\b(?:gratis|gratuit[oa]s?|acceso libre|entrada libre)\b",
            sentence, re.I))
        return {
            "title": title,
            "start": stamp.isoformat() + "T" + start.strftime("%H:%M:%S"),
            "end": (stamp.isoformat() + "T" + end.strftime("%H:%M:%S")) if end else None,
            "municipality": TOWN,
            "venue": SP_VENUE,
            "category": "familia" if re.search(
                r"infantil|familiar|niñ|papa noel|papá noel|lego|taller",
                normalized(title)) else "ocio",
            "free": 1 if price_known_free else None,
            "price": "Entrada libre" if price_known_free else "",
            "details": info,
            "source_name": SP_NAME,
            "source_url": source_url,
            "status": "approved",
            "image_url": siete_palmas_official_image(soup),
            "image_origin": source_url,
            "image_alt": "Imagen oficial del programa de Siete Palmas",
            "image_status": "official_remote" if siete_palmas_official_image(soup) else ""
        }
    return None


def synchronize_siete_palmas(conn, now, today, upsert, fetch_html):
    found = added = changed = checked = 0
    error = ""
    try:
        links = siete_palmas_links(fetch_html(SP_URL))
        if not links:
            raise ValueError("No official articles found in the events feed")
        problems = []
        for url in links[:8]:
            try:
                item = extract_siete_palmas_article(fetch_html(url), url, today)
                checked += 1
                if not item:
                    continue
                result = upsert(conn, item)
                found += 1
                added += int(result == "added")
                changed += int(result == "changed")
            except Exception as exc:
                problems.append(type(exc).__name__ + ": " + str(exc)[:80])
        if problems:
            error = "; ".join(problems[:2])[:200]
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)[:180]
    conn.execute("""INSERT INTO source_log(source,checked_at,found,added,changed,error)
        VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
        checked_at=excluded.checked_at,found=excluded.found,
        added=excluded.added,changed=excluded.changed,error=excluded.error""",
        (SP_NAME, str(now), found, added, changed, error))
    conn.commit()
    return {"source": SP_NAME, "checked_at": str(now), "found": found,
            "added": added, "changed": changed, "error": error,
            "articles_checked": checked, "official_url": SP_URL}
