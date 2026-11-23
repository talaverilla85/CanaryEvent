"""Small, strict adapter for images in independently verified municipal articles.

An event must already pass the existing date/venue/source verification.
Only image links attached to the exact official article are considered; do
not guess artwork from a title, a social-media post, or generic page chrome.
"""
from __future__ import annotations

from urllib.parse import urljoin, urlsplit
from event_images import image_fields

GUIA_SLUG = (
    "/guia-dara-la-bienvenida-a-la-navidad-el-proximo-jueves-26-de-"
    "noviembre-con-el-tradicional-encendido-de-luces-y-el-concierto-"
    "de-navidad-de-la-trova/"
)
VEGA_SLUG = (
    "/noticia/se-abre-el-plazo-para-participar-en-el-iii-mercado-"
    "navideno-de-san-mateo"
)


def _safe_image(raw, source_url, hosts, prefix, suffixes):
    try:
        image = urljoin(source_url, str(raw or "").strip())
        parsed = urlsplit(image)
        if (parsed.scheme == "https" and parsed.hostname in hosts
                and parsed.path.startswith(prefix)
                and parsed.path.lower().endswith(suffixes)
                and parsed.username is None and parsed.password is None):
            return image
    except (TypeError, ValueError):
        pass
    return ""


def from_official_article(soup, source_url):
    """Return verified image fields, or {} when no correct poster is present."""
    try:
        article_url = urlsplit(source_url)
    except (ValueError, TypeError):
        return {}
    if article_url.scheme != "https":
        return {}

    image, alt = "", ""
    if (article_url.hostname == "santamariadeguia.es"
            and article_url.path == GUIA_SLUG):
        meta = soup.select_one('meta[property="og:image"][content]')
        image = _safe_image(
            meta.get("content") if meta else "", source_url,
            {"santamariadeguia.es"}, "/wp-content/uploads/2026/11/",
            (".jpg", ".jpeg", ".png", ".webp"))
        alt = "Imagen oficial de la noticia sobre el encendido navideño de Guía"
    elif (article_url.hostname in {"www.vegadesanmateo.es",
                                  "vegadesanmateo.es"}
          and article_url.path == VEGA_SLUG):
        # Drupal exposes an actual 2026 event poster, alongside a link to
        # the full-resolution asset. Ignore site logos or unrelated teasers.
        posters = [
            tag for tag in soup.select('img[alt]')
            if "cartel iii mercado navideño 2026" in
            tag.get("alt", "").casefold()
        ]
        if posters:
            image = _safe_image(
                "/sites/default/files/noticias/Cartel.jpg",
                source_url, {"www.vegadesanmateo.es",
                             "vegadesanmateo.es"},
                "/sites/default/files/noticias/", (".jpg",))
            # Confirm this original is linked by the displayed poster, not
            # a fabricated asset path that happens to exist on the host.
            has_original = any(
                _safe_image(a.get("href"), source_url,
                    {"www.vegadesanmateo.es", "vegadesanmateo.es"},
                    "/sites/default/files/noticias/", (".jpg",))
                == image
                for a in soup.select('a[href]')
            )
            if not has_original:
                image = ""
        alt = "Cartel oficial del III Mercado Navideño 2026 de Vega de San Mateo"
    if not image:
        return {}
    return image_fields(image, alt, source_url)


GUIA_URL = "https://santamariadeguia.es" + GUIA_SLUG
VEGA_URL = "https://www.vegadesanmateo.es" + VEGA_SLUG


def backfill_approved_missing(conn, now, today, fetch_html):
    """Repair existing records even after their articles leave the news feed.

    Only two explicitly verified municipal URLs are eligible. Never overwrite
    artwork already supplied by an editor or imported from another source.
    The official page must still expose its own matching image.
    """
    updated, checked, failures = 0, 0, []
    for url in (GUIA_URL, VEGA_URL):
        rows = conn.execute(
            """SELECT id FROM events WHERE source_url=? AND status='approved'
               AND COALESCE(image_url,'')=''
               AND substr(coalesce("end",start),1,10)>=?""",
            (url, today.isoformat()),
        ).fetchall()
        if not rows:
            continue
        try:
            image = from_official_article(fetch_html(url), url)
            checked += 1
            if not image:
                failures.append({"source_url": url, "reason": "no_verified_image"})
                continue
            for row in rows:
                cur = conn.execute(
                    """UPDATE events SET image_url=?,image_alt=?,image_origin=?,
                       image_status=?,updated_at=? WHERE id=?
                       AND COALESCE(image_url,'')='' AND status='approved'""",
                    (image["image_url"], image["image_alt"],
                     image["image_origin"], image["image_status"],
                     str(now), row["id"]),
                )
                updated += cur.rowcount
        except Exception as exc:
            failures.append({"source_url": url, "reason": type(exc).__name__})
    return {"source": "Carteles municipales oficiales contrastados",
            "checked_at": str(now), "found": checked,
            "added": 0, "changed": updated,
            "error": "; ".join(x["reason"] for x in failures)[:200]}
