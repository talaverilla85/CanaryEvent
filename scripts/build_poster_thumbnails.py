#!/usr/bin/env python3
"""Build bounded, static WebP thumbnails from already verified official posters.

Only Cabildo's known GridFS image endpoint is accepted. This intentionally
does not generate thumbnails through a Vercel paid image transformation service.

The original image_url, image_origin and source_url remain in the catalogue.
A small static manifest maps verified originals to immutable local thumbnails.
Image fetching honours robots.txt, redirects are not followed, and every image
is size/pixel bounded before Pillow processes it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from io import BytesIO
import json
import re
import sys
import time
from pathlib import Path
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps, UnidentifiedImageError
import requests

ROOT=Path(__file__).resolve().parents[1]
POSTERS=ROOT/"public"/"posters"
CATALOG=ROOT/"public"/"events.json"
MANIFEST=POSTERS/"manifest.js"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
ROOT_URL="https://www.eventosgrancanaria.com"
IMAGE_URL=re.compile(
    r"https://www\.eventosgrancanaria\.com/controlpanel/files/gridfs/[a-fA-F0-9]{24}\Z"
)
MAX_BYTES=12*1024*1024
MAX_PIXELS=36_000_000
MAX_WEBP_BYTES=200*1024
MAX_IMAGES_PER_PASS=80
MAX_SCANNED_POSTERS=350
HORIZON_DAYS=120
THROTTLE_SECONDS=0.15
HEADERS={
    "User-Agent":AGENT,
    "Accept":"image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8",
}


def valid_official_url(value):
    return isinstance(value,str) and bool(IMAGE_URL.fullmatch(value))


def poster_filename(url):
    """Use the organizer-assigned immutable GridFS identifier, not event IDs."""
    if not valid_official_url(url):
        raise ValueError("Poster image is not an allowlisted official GridFS URL")
    return url.rsplit("/",1)[1].lower()+".webp"


def candidates(events,now=None):
    """Prioritize upcoming performances; keep original poster provenance."""
    today=(now or datetime.now(ZoneInfo("Atlantic/Canary"))).date()
    end=today+timedelta(days=HORIZON_DAYS)
    selected={}
    for event in events:
        if not isinstance(event,dict) or event.get("paid_promotion") is True:
            continue
        if event.get("image_status")!="official_remote":
            continue
        url=event.get("image_url")
        if not valid_official_url(url):
            continue
        start=str(event.get("start") or "")[:10]
        try:
            date=datetime.strptime(start,"%Y-%m-%d").date()
        except ValueError:
            continue
        if not today<=date<=end:
            continue
        # Earliest upcoming use determines optimization order.
        if url not in selected or date<selected[url]:
            selected[url]=date
    return [url for url,_ in sorted(selected.items(),key=lambda x:(x[1],x[0]))][:MAX_SCANNED_POSTERS]


def check_robots(session):
    """Respect the official site's crawler policy, fail closed on errors."""
    response=session.get(
        ROOT_URL+"/robots.txt",
        headers={"User-Agent":AGENT,"Accept":"text/plain"},
        timeout=(5,15),
        allow_redirects=False,
    )
    if response.status_code not in (200,404,410):
        raise RuntimeError("Official poster robots.txt unavailable (HTTP "+str(response.status_code)+")")
    rp=RobotFileParser()
    if response.status_code==200:
        rp.parse(response.text.splitlines())
    else:
        rp.allow_all=True
    return rp


def download_original(session,url,policy):
    if not valid_official_url(url):
        raise ValueError("Poster URL not allowlisted")
    if not policy.can_fetch(AGENT,url):
        raise PermissionError("Official poster image disallowed by robots.txt")
    response=session.get(url,headers=HEADERS,timeout=(5,20),
                         allow_redirects=False,stream=True)
    try:
        if response.status_code!=200:
            raise RuntimeError("Official poster returned HTTP "+str(response.status_code))
        content_type=response.headers.get("Content-Type","").split(";")[0].lower().strip()
        if content_type not in ("image/jpeg","image/png","image/webp",
                                "application/octet-stream"):
            raise ValueError("Remote resource is not an allowed image type")
        size_header=response.headers.get("Content-Length","")
        if size_header and int(size_header)>MAX_BYTES:
            raise ValueError("Poster source too large")
        chunks=[]
        size=0
        for chunk in response.iter_content(chunk_size=131072):
            if not chunk:
                continue
            size+=len(chunk)
            if size>MAX_BYTES:
                raise ValueError("Poster download exceeded byte limit")
            chunks.append(chunk)
        if not size:
            raise ValueError("Official poster is empty")
        return b"".join(chunks)
    finally:
        response.close()


def compress_webp(data):
    """Aspect-preserving, un-cropped 760px poster; keep official wording intact."""
    if len(data)>MAX_BYTES:
        raise ValueError("Original exceeds byte limit")
    with Image.open(BytesIO(data)) as original:
        if original.format not in ("JPEG","PNG","WEBP"):
            raise ValueError("Unexpected poster image format")
        if original.width*original.height>MAX_PIXELS:
            raise ValueError("Original image exceeds pixel limit")
        image=ImageOps.exif_transpose(original)
        image.thumbnail((760,960),Image.Resampling.LANCZOS)
        if image.mode not in ("RGB","RGBA"):
            image=image.convert("RGBA" if "A" in image.getbands() else "RGB")
        for quality in (69,57,47):
            destination=BytesIO()
            image.save(destination,format="WEBP",quality=quality,method=5)
            encoded=destination.getvalue()
            if len(encoded)<=MAX_WEBP_BYTES:
                return encoded
    raise ValueError("Thumbnail would exceed 200 KiB")


def manifest_content(mapping):
    """JavaScript only contains local verified paths and allowlisted source URLs."""
    clean={}
    for url,local in sorted(mapping.items()):
        if (valid_official_url(url) and
            re.fullmatch(r"/posters/[a-f0-9]{24}\.webp",str(local))):
            clean[url]=local
    return ("// Auto-generated static thumbnails. Official source URLs remain in events.json.\n"+
            "window.DParrandaPosterThumbs=Object.freeze("+
            json.dumps(clean,ensure_ascii=True,separators=(",",":"))+
            ");\n")


def generate(events,out_dir,session=None,now=None,max_new=MAX_IMAGES_PER_PASS,
             policy=None,delay=THROTTLE_SECONDS):
    session=session or requests.Session()
    urls=candidates(events,now)
    out_dir=Path(out_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    if policy is None:
        policy=check_robots(session)
    mapping={}
    added=0
    failures=0
    source_bytes=0
    optimized_bytes=0
    for url in urls:
        filename=poster_filename(url)
        target=out_dir/filename
        if target.exists() and 0<target.stat().st_size<=MAX_WEBP_BYTES:
            mapping[url]="/posters/"+filename
            optimized_bytes+=target.stat().st_size
            continue
        if added>=max_new:
            continue
        try:
            source=download_original(session,url,policy)
            thumb=compress_webp(source)
            if len(thumb)>=len(source):
                raise ValueError("No compression benefit")
            temp=target.with_suffix(".tmp")
            temp.write_bytes(thumb)
            temp.replace(target)
            mapping[url]="/posters/"+filename
            added+=1
            source_bytes+=len(source)
            optimized_bytes+=len(thumb)
        except (requests.RequestException,RuntimeError,PermissionError,ValueError,
                OSError,UnidentifiedImageError) as error:
            failures+=1
            print("Poster deferred:",filename,type(error).__name__,str(error)[:90],flush=True)
        if delay:
            time.sleep(delay)
    # Keep any valid thumbnail already built for current records and safely
    # discard old posters that no longer appear in the rolling official catalog.
    retained={p.rsplit("/",1)[1] for p in mapping.values()}
    for old in out_dir.glob("*.webp"):
        if old.name not in retained and re.fullmatch(r"[a-f0-9]{24}\.webp",old.name):
            old.unlink()
    (out_dir/"manifest.js").write_text(manifest_content(mapping),encoding="utf-8")
    return {"candidates":len(urls),"available":len(mapping),"new":added,
            "failures":failures,"source_bytes":source_bytes,
            "thumbnail_bytes":optimized_bytes}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--max-new",type=int,default=MAX_IMAGES_PER_PASS)
    args=parser.parse_args()
    if args.max_new<0 or args.max_new>160:
        parser.error("--max-new must be 0..160")
    events=json.loads(CATALOG.read_text(encoding="utf-8"))["events"]
    try:
        result=generate(events,POSTERS,max_new=args.max_new)
    except (requests.RequestException,RuntimeError,ValueError) as error:
        # A genuine remote outage is not permission to bypass a robots gate.
        print("Poster source unavailable; existing thumbnails kept:",str(error),file=sys.stderr)
        sys.exit(2)
    print("Static WebP poster optimization:",json.dumps(result,ensure_ascii=False))
    if result["new"]==0 and result["available"]==0:
        print("No verified image could be converted; originals remain as fallback.")


if __name__=="__main__":
    main()
