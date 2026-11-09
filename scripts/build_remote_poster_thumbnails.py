#!/usr/bin/env python3
"""Safely cache official public JPEG/PNG posters from two verified Canary sources.

Only specific WordPress uploads paths on the existing official-event hosts are
eligible; robots.txt must permit access, redirects are refused, downloads are
strictly bounded, and the original official URL remains in events.json.
This runs at publication time, never on a visitor request.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from PIL import UnidentifiedImageError
from zoneinfo import ZoneInfo
import json
import re
import time

import requests
import build_poster_thumbnails as poster

ROOT=Path(__file__).resolve().parents[1]
POSTERS=ROOT/"public"/"posters"
CATALOG=ROOT/"public"/"events.json"
MANIFEST=POSTERS/"remote-manifest.js"
HOSTS=("eventos.santabrigida.es","ingenio.es")
PATH_RE=re.compile(
    r"/wp-content/uploads/20[0-9]{2}/(?:0[1-9]|1[0-2])/[A-Za-z0-9_.-]+\.(?:jpeg|jpg|png|webp)\Z",re.I
)
MAX_NEW=12
MAX_CANDIDATES=120
HORIZON_DAYS=120
ROBOT_REQUEST_TIMEOUT=(5,12)
POSTER_REQUEST_TIMEOUT=(5,20)


def valid_official_url(url):
    if not isinstance(url,str) or len(url)>600:
        return False
    try:
        parts=urlsplit(url)
    except ValueError:
        return False
    return (parts.scheme=="https" and parts.netloc in HOSTS and
            not parts.username and not parts.password and
            not parts.query and not parts.fragment and
            bool(PATH_RE.fullmatch(parts.path)))


def poster_id(url):
    if not valid_official_url(url):
        raise ValueError("Image is not a trusted official uploads URL")
    return "r-"+sha256(url.encode("utf8")).hexdigest()[:24]


def filenames(url):
    key=poster_id(url)
    return {width:key+f"-{width}.webp" for width in poster.CARD_WIDTHS} | {
        "detail":key+".webp"
    }


def candidates(events,now=None):
    today=(now or datetime.now(ZoneInfo("Atlantic/Canary"))).date()
    horizon=today+timedelta(days=HORIZON_DAYS)
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
        until=str(event.get("end") or start)[:10]
        try:
            first=datetime.strptime(start,"%Y-%m-%d").date()
            last=datetime.strptime(until,"%Y-%m-%d").date()
        except ValueError:
            continue
        if first>last or last<today or first>horizon:
            continue
        priority=max(today,first)
        if url not in selected or priority<selected[url]:
            selected[url]=priority
    return [u for u,_ in sorted(selected.items(),key=lambda kv:(kv[1],kv[0]))][:MAX_CANDIDATES]


def robots_for(session,host):
    response=session.get(
        "https://"+host+"/robots.txt",
        headers={"User-Agent":poster.AGENT,"Accept":"text/plain"},
        timeout=ROBOT_REQUEST_TIMEOUT,allow_redirects=False,
    )
    try:
        if response.status_code not in (200,404,410):
            raise PermissionError("Robots unavailable for "+host)
        rules=RobotFileParser()
        if response.status_code==200:
            rules.parse(response.text.splitlines())
        else:
            rules.allow_all=True
        return rules
    finally:
        response.close()


def manifest_content(mapping):
    clean={}
    for url,paths in sorted(mapping.items()):
        if not valid_official_url(url) or not isinstance(paths,dict):
            continue
        names=filenames(url)
        if all(paths.get(key)=="/posters/"+filename for key,filename in
               (("thumb",names[320]),("retina",names[480]),("detail",names["detail"]))):
            clean[url]=paths
    return ("// Official external images cached at publication time; original URLs remain in events.json.\n"
            "window.DParrandaExtraPosterThumbs=Object.freeze("+
            json.dumps(clean,ensure_ascii=True,separators=(",",":"))+");\n")


def generate(events,out_dir,session=None,now=None,max_new=MAX_NEW,delay=0.15):
    if not 0<=max_new<=80:
        raise ValueError("Invalid per-pass download limit")
    out_dir=Path(out_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    session=session or requests.Session()
    targets=candidates(events,now)
    policies={}
    mapping={}
    created=0
    failures=0
    bytes_before=0
    bytes_after=0
    retained=set()
    for url in targets:
        host=urlsplit(url).netloc
        if host not in policies:
            try:
                policies[host]=robots_for(session,host)
            except (requests.RequestException,RuntimeError,PermissionError,ValueError) as exc:
                policies[host]=None
                print("Remote poster host deferred:",host,type(exc).__name__,flush=True)
        rules=policies[host]
        if not rules or not rules.can_fetch(poster.AGENT,url):
            continue  # No robots permission -> never fetch or show a new local copy.
        names=filenames(url)
        existing=all((out_dir/name).is_file() and 0<(out_dir/name).stat().st_size<=
                     (poster.MAX_WEBP_BYTES if key=="detail" else poster.MAX_CARD_BYTES)
                     for key,name in names.items())
        if not existing and created>=max_new:
            continue
        try:
            if not existing:
                source=download_official(session,url)
                encoded=poster.compress_webp(source)
                if len(encoded)>=len(source):
                    raise ValueError("Optimized image would not save bytes")
                outputs={"detail":encoded}
                outputs.update({w:poster.compress_card(encoded,w) for w in poster.CARD_WIDTHS})
                for key,data in outputs.items():
                    file=out_dir/names[key]
                    temporary=file.with_suffix(".tmp")
                    temporary.write_bytes(data)
                    temporary.replace(file)
                created+=1
                bytes_before+=len(source)
                bytes_after+=sum(map(len,outputs.values()))
            mapping[url]={"thumb":"/posters/"+names[320],
                          "retina":"/posters/"+names[480],
                          "detail":"/posters/"+names["detail"]}
            retained.update(names.values())
        except (requests.RequestException,RuntimeError,PermissionError,ValueError,
                OSError,UnidentifiedImageError) as exc:
            failures+=1
            print("External poster deferred:",poster_id(url),type(exc).__name__,
                  str(exc)[:75],flush=True)
        if delay:
            time.sleep(delay)
    # Keep old immutable derivatives on a transient robots/server outage.
    # Do not delete working media merely because the host could not be reached.
    (out_dir/"remote-manifest.js").write_text(manifest_content(mapping),encoding="utf8")
    return {"candidates":len(targets),"available":len(mapping),"new":created,
            "deferred":failures,"original_bytes":bytes_before,
            "variants_bytes":bytes_after}


def download_official(session,url):
    if not valid_official_url(url):
        raise ValueError("Remote URL not trusted")
    response=session.get(url,headers=poster.HEADERS,
        timeout=POSTER_REQUEST_TIMEOUT,allow_redirects=False,stream=True)
    try:
        if response.status_code!=200:
            raise RuntimeError("Official poster returned HTTP "+str(response.status_code))
        mime=response.headers.get("Content-Type","").split(";")[0].lower().strip()
        if mime not in ("image/jpeg","image/png","image/webp"):
            raise ValueError("Only image mime types are allowed")
        size_header=response.headers.get("Content-Length")
        if size_header:
            try:
                stated=int(size_header)
            except (TypeError,ValueError) as exc:
                raise ValueError("Invalid Content-Length") from exc
            if stated>poster.MAX_BYTES or stated<0:
                raise ValueError("Image too large")
        chunks=[]
        total=0
        for chunk in response.iter_content(chunk_size=131072):
            if not chunk:continue
            total+=len(chunk)
            if total>poster.MAX_BYTES:
                raise ValueError("Image byte limit exceeded")
            chunks.append(chunk)
        if total==0:raise ValueError("Empty official image")
        return b"".join(chunks)
    finally:
        response.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--max-new",type=int,default=MAX_NEW)
    args=parser.parse_args()
    events=json.loads(CATALOG.read_text("utf8"))["events"]
    result=generate(events,POSTERS,max_new=args.max_new)
    print("Static official remote posters:",json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
