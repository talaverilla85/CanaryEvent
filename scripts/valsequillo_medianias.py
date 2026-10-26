"""Valsequillo 2026: two verified days of Alma de Medianías.

Official organizer: Mancomunidad de Municipios de las Medianías de Gran Canaria.
This is a 2026-specific connector, not a generic municipal crawler.
The Valsequillo municipal HTTPS issue must not be bypassed by disabling TLS.
"""
from __future__ import annotations
import datetime as dt
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

NAME = "Mancomunidad de Medianías · Alma de Medianías en Valsequillo"
URL = ("https://www.medianias.org/noticias/"
       "la-mancomunidad-de-medianias-invita-a-toda-la-isla-a-su-mesa-"
       "alma-de-medianias-del-31-de-octubre-al-1-de-noviembre-en-valsequillo/4307")
BASE = "https://www.medianias.org"
AGENT = "CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS = {"User-Agent": AGENT, "Accept": "text/html,application/xhtml+xml"}
END_DATE = dt.date(2026, 11, 1)

REQUIRED_PHRASES = (
    "Alma de Medianías", "31 de octubre", "1 de noviembre", "Valsequillo",
    "Pabellón Municipal El Mercadillo", "10:00 a 19:00",
    "10:00 a 16:00", "entrada libre y gratuita"
)

def fetch(client=requests):
    """Respect robots and request official notice via verified HTTPS."""
    robots = client.get(BASE + "/robots.txt", headers=HEADERS,
                        timeout=12, allow_redirects=False)
    if robots.status_code == 200:
        rule = RobotFileParser()
        rule.parse(robots.text.splitlines())
        if not rule.can_fetch(AGENT, URL):
            raise PermissionError("Mancomunidad robots.txt disallows this notice")
    elif robots.status_code not in (404, 410):
        raise RuntimeError(f"Mancomunidad robots HTTP {robots.status_code}")
    response = client.get(URL, headers=HEADERS, timeout=25,
                          allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f"Mancomunidad notice HTTP {response.status_code}")
    if len(response.content) > 1_500_000:
        raise ValueError("Official notice response unexpectedly large")
    return BeautifulSoup(response.content, "html.parser")

def extract(soup, today, places, categorize):
    if "Valsequillo" not in places or today > END_DATE:
        return []
    if today < dt.date(2026, 9, 1):
        return []
    main = soup.select_one("article") or soup.select_one("main") or soup.body
    if main is None:
        raise ValueError("Mancomunidad notice has no readable body")
    content = " ".join(main.get_text(" ", strip=True).split()).casefold()
    missing = [phrase for phrase in REQUIRED_PHRASES
               if phrase.casefold() not in content]
    if missing:
        raise ValueError("Official announcement missing facts: " + ", ".join(missing))
    sessions = (
        ("2026-10-31T10:00:00", "2026-10-31T19:00:00"),
        ("2026-11-01T10:00:00", "2026-11-01T16:00:00"),
    )
    return [
        {
            "title": "Alma de Medianías 2026 · Feria Regional de Vino, Queso y Miel",
            "start": start, "end": end, "municipality": "Valsequillo",
            "venue": "Pabellón Municipal El Mercadillo y alrededores",
            "category": categorize("feria vino queso miel gastronomía"),
            "free": 1, "price": "Gratis",
            "details": (
                "Feria de productores artesanos de Canarias, con vino, queso, "
                "miel, catas, talleres y música. Consulta posibles cambios en "
                "la convocatoria oficial de la Mancomunidad."
            ),
            "source_name": NAME, "source_url": URL, "status": "approved",
        }
        for start, end in sessions if start[:10] >= today.isoformat()
    ]
