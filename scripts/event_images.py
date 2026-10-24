"""Extract only event-specific remotely hosted images from recognized source pages.

URLs point to original publisher/CDN: we do not download or rehost files.
Always attribute the publisher and show a neutral no-photo fallback when missing.
"""
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

HOSTS = {
 "ingenio.es","www.ingenio.es",
 "eventos.aguimes.es","actividadesjuventud.laspalmasgc.es",
 "artesescenicasgrancanaria.com","www.artesescenicasgrancanaria.com",
 "www.eventosgrancanaria.com"
}
DISALLOWED = (
 "favicon", "logo", "og-image.jpg", "default", "placeholder", "sin-imagen",
 "categories/", "icons/", "avatar", "rrss", "social", "noimage"
)

def image_url(raw,base):
    if not isinstance(raw,str) or not raw.strip():return ""
    url=urljoin(base,raw.strip())
    try:
        p=urlsplit(url)
        if p.scheme!="https" or p.hostname not in HOSTS:return ""
        if p.username or p.password:return ""
        if len(url)>800:return ""
        path=p.path.lower()
        if any(part in path for part in DISALLOWED):return ""
        # The official Cabildo serves binary images without an extension.
        if not (path.endswith((".jpg",".jpeg",".png",".webp",".avif")) or
                (p.hostname=="www.eventosgrancanaria.com" and path.startswith("/controlpanel/files/gridfs/"))):
            return ""
        return url
    except (TypeError,ValueError):
        return ""

def listing_image(node,base,selectors):
    for selector in selectors:
        el=node.select_one(selector)
        if not el:continue
        raw=el.get("data-src") or el.get("src") or el.get("data-lazy-src")
        url=image_url(raw,base)
        if url:return url
    return ""

def official_page_image(soup,page_url):
    # Generic site social banner is NEVER used as an event cover.
    for key in ("og:image","twitter:image"):
        el=soup.select_one(('meta[property="%s"]' if key=="og:image" else 'meta[name="%s"]') % key)
        if el:
            result=image_url(el.get("content"),page_url)
            if result:return result
    return listing_image(soup,page_url,[
      ".event-detail__wrapper-image img",
      ".event-detail__image img"
    ])

def image_fields(url,title,publisher):
    image=bool(url)
    return {
       "image_url":url or "",
       "image_alt":title[:180] if image else "",
       "image_origin":publisher if image else "",
       "image_status":"official_remote" if image else "not_available"
    }
