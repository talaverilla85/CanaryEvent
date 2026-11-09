#!/usr/bin/env python3
"""Publish one bounded, official first-paint preview in the static homepage.

The daily poster workflow runs this after verified WebP generation. Never fetch
an external image here: only a locally existing, verified official thumbnail
may appear in the initial HTML. Live /api/catalog always remains authoritative.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/"public/index.html"
EVENTS=ROOT/"public/events.json"
POSTERS=ROOT/"public/posters"
MANIFESTS=(POSTERS/"manifest.js",POSTERS/"remote-manifest.js")
START_PRELOAD="<!-- DPARRANDA_FEATURE_PRELOAD_START -->"
END_PRELOAD="<!-- DPARRANDA_FEATURE_PRELOAD_END -->"
START_IMAGE="<!-- DPARRANDA_FEATURE_IMAGE_START -->"
END_IMAGE="<!-- DPARRANDA_FEATURE_IMAGE_END -->"
LOCAL_WEBP=re.compile(r"/posters/(?:r-)?[a-f0-9]{24}-320\.webp\Z")


def load_manifest(path):
    text=path.read_text(encoding="utf8")
    match=re.search(r"Object\.freeze\((\{.*\})\);",text,re.S)
    if not match:
        raise ValueError("Poster manifest is malformed")
    data=json.loads(match.group(1))
    if not isinstance(data,dict):
        raise ValueError("Poster manifest is not an object")
    return data


def choose(events,mapping,posters,today):
    """Follow official catalogue order; default home picks its first dated image."""
    for item in events:
        if not isinstance(item,dict) or item.get("paid_promotion") is True:
            continue
        if item.get("image_status")!="official_remote":
            continue
        title=item.get("title")
        if not isinstance(title,str) or not title.strip():
            continue
        start=str(item.get("start") or "")[:10]
        last=str(item.get("end") or start)[:10]
        if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}",start) and
                re.fullmatch(r"\d{4}-\d{2}-\d{2}",last) and
                start<=today<=last):
            continue
        paths=mapping.get(item.get("image_url"))
        if not isinstance(paths,dict):
            continue
        src=paths.get("thumb","")
        if not isinstance(src,str) or not LOCAL_WEBP.fullmatch(src):
            continue
        file=posters/src.rsplit("/",1)[1]
        if not file.is_file() or not 0<file.stat().st_size<=80*1024:
            continue
        return src,title,str(item.get("id"))
    return None


def between(text,start,end,generated):
    if text.count(start)!=1 or text.count(end)!=1:
        raise ValueError("Homepage preview markers must occur exactly once")
    left,after=text.split(start,1)
    _,right=after.split(end,1)
    return left+start+"\n"+generated+end+right


def update(html,events,mapping,posters,today):
    chosen=choose(events,mapping,posters,today)
    if chosen:
        src,title,event_id=chosen
        safe_title=escape(title,quote=True)
        preload=('<link rel="preload" as="image" href="'+src+
                 '" fetchpriority="high">\n')
        image=('<img src="'+src+'" alt="Imagen del evento '+safe_title+
               '" loading="eager" decoding="async" fetchpriority="high"'+
               ' data-feature-preview-date="'+today+'"'+
               ' data-feature-preview-id="'+escape(event_id,quote=True)+'">\n')
    else:
        preload=""
        image=""
    html=between(html,START_PRELOAD,END_PRELOAD,preload)
    return between(html,START_IMAGE,END_IMAGE,image)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    catalog=json.loads(EVENTS.read_text(encoding="utf8"))["events"]
    mapping={}
    for path in MANIFESTS:
        mapping.update(load_manifest(path))
    today=datetime.now(ZoneInfo("Atlantic/Canary")).date().isoformat()
    before=HOME.read_text(encoding="utf-8-sig")
    after=update(before,catalog,mapping,POSTERS,today)
    if args.check:
        if before!=after:
            raise SystemExit("Initial featured image is not synchronized")
    elif before!=after:
        HOME.write_text(after,encoding="utf-8-sig")
        print("Updated early featured image for",today)
    else:
        print("Early featured image already synchronized for",today)


if __name__=="__main__":
    main()
