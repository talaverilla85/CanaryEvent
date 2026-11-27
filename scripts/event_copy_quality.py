"""Editorial safeguards for scraped event copy before SQLite / JSON / Postgres.

The organiser's listing sometimes embeds WordPress HTML/Read More links in
descriptions. Extract plain text safely; never expose HTML syntax in an event.
One official Santa Brígida excursion has additional verified, time-bounded facts
which the municipal index omitted. Those facts must not be used in later years.
"""
from __future__ import annotations

import html
import re
from bs4 import BeautifulSoup

TRIP_SOURCE = (
    "https://eventos.santabrigida.es/eventos/"
    "salida-cultural-jardin-de-la-marquesa/"
)
TRIP_DATE = "2026-11-27"
TRIP_VENUE = "Club Municipal de Mayores de Santa Brígida"


def plain_description(value):
    """Remove publisher markup and 'Read more' furniture without deleting text."""
    text = html.unescape(str(value or "").replace("\\n", " ").replace("\\t", " "))
    has_markup = bool(re.search(r"<\s*[/!]?\s*[a-z][^>]*>", text, re.I))
    has_teaser = False
    if has_markup:
        soup = BeautifulSoup(text, "html.parser")
        for a in soup.select("a.read-more, a[aria-label^='Leer más'], .read-more"):
            has_teaser = True
            a.decompose()
        for bad in soup.select("script, style, iframe, svg"):
            bad.decompose()
        text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    if has_teaser or re.search(r"\s(?:Leer más|Leer mas)\s*$", text, re.I):
        text = re.sub(r"\s*(?:\.\.\.|…)\s*(?:Leer m[aá]s)?\s*$", "", text, flags=re.I)
        text = text.rstrip(" .") + ". Consulta la publicación original para ampliar la información."
    return text


def normalize_event(record):
    """Return copy with verified content and safe plain text; never infer coordinates."""
    item = dict(record)
    item["details"] = plain_description(item.get("details", ""))
    if (item.get("source_url") == TRIP_SOURCE and
            str(item.get("start", "")).startswith(TRIP_DATE) and
            item.get("source_name", "").startswith("Ayuntamiento de Santa Brígida")):
        item["venue"] = TRIP_VENUE
        item["price"] = "16 € almuerzo + 6 € entrada"
        item["free"] = 0
        item["details"] = (
            "Salida cultural organizada por el Club Municipal de Mayores de "
            "Santa Brígida para visitar el Jardín de la Marquesa, en Arucas, "
            "con almuerzo posterior en el Restaurante Balcón de Zamora, "
            "en Valleseco. Precio anunciado: 16 € por el almuerzo y 6 € "
            "por la entrada al jardín; transporte y seguro gratuitos a "
            "cargo de la Concejalía de Mayores y Servicios Sociales. "
            "Actividad dirigida a socios del Club de Mayores; el público "
            "general solo puede participar si quedan plazas libres. "
            "Inscripción presencial anunciada del 16 al 18 de noviembre "
            "(8:00–14:00), o hasta completar aforo. "
            "Información: 928 644 242. "
            "La fuente identifica el Club de Mayores como local, "
            "pero no confirma el punto exacto de encuentro o salida. "
            "Consulta a la organización antes de desplazarte."
        )
    return item
