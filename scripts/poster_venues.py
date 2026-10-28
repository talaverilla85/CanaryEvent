"""Small, source-restricted pilot: read event venues printed only on posters.

Proof requirements:
- exact approved Cabildo event and its *own* official remote cover image
- robots-allowed HTTPS JPEG/PNG/WebP, bounded bytes; no external image fetches
- no automatic publication on one AI response
- two independent visual passes agree on title, date and named venue
- source image SHA256 is recorded, old/changed posters never silently reused
- documented human visual review of one verified poster is separately pinned
- strict requests/day and per-run budget, with failed calls counted
Images and API keys are never stored in the repository.
"""
from __future__ import annotations
import base64
import datetime as dt
import hashlib
import io
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from PIL import Image
import venue_quality
from telde_pdf_vision import MODEL, response_usage_cost

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/"data"/"poster_venue_pilot"/"reviewed.json"
REPORT=ROOT/"data"/"poster_venue_pilot"/"report.json"
AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HOST="www.eventosgrancanaria.com"
BASE="https://"+HOST
IMAGE_PATH=re.compile(r"/controlpanel/files/gridfs/[a-f0-9]{24}")
EVENT_PATH=re.compile(r"/event/E-20\d{6}-\d{4}/[a-z0-9%_-]+")
HEADERS={"User-Agent":AGENT,"Accept":"image/jpeg,image/png,image/webp"}
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio",
        "agosto","septiembre","octubre","noviembre","diciembre")
VERSION="poster-venues-v1"
MAX_IMAGE_BYTES=2_000_000
MAX_POSTERS_PER_RUN=3
MAX_API_CALLS=6
MAX_COST_USD=0.035
# A 31 October 2026 official Cabildo JPEG was visually verified directly
# against the flyer shared by a user. Pin its exact original image digest.
MANUALLY_VERIFIED={
    "https://www.eventosgrancanaria.com/event/E-20261031-0013/noche-de-finaos":{
        "title":"Noche de Finaos","municipality":"Mogán",
        "start_day":"2026-10-31","venue":"Parque Nicolás Quesada",
        "poster_sha256":"f6670136a87e95103a5be675dd902c302802e52ae9a23932325aceb53e2c1cde",
        "poster_image_url":"https://www.eventosgrancanaria.com/controlpanel/files/gridfs/6ad718cb013a6268e07a7c2a",
        "reference":"2026-10-27 user-supplied screenshot of official poster"
    }
}
SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{
    "one_event_single_venue":{"type":"boolean"},
    "poster_title":{"type":"string"},
    "date_text":{"type":"string"},
    "venue":{"type":"string"},
    "venue_evidence":{"type":"string"}
 },
 "required":["one_event_single_venue","poster_title","date_text","venue","venue_evidence"]
}
PROMPT=(
 "Lee ÚNICAMENTE las letras visibles en este cartel de un evento de Gran Canaria. "
 "Un evento puede anunciar actos en recintos distintos: en ese caso no selecciones uno "
 "a menos que sea inequívoco que la sede del evento consultado es UNA sola. "
 "Devuelve un título del propio cartel, la fecha exactamente como esté impresa "
 "(no completes año si no se lee), el recinto preciso y una cita CORTA literal de "
 "la línea del recinto. Si falta la sede, no puedes leer el texto, o hay varias "
 "sedes posibles, devuelve one_event_single_venue=false y venue vacío. "
 "Nunca uses la dirección del organizador ni el centro del municipio."
)
SECOND_PROMPT=(
 "Realiza una lectura INDEPENDIENTE del cartel. Transcribe el nombre concreto "
 "del edificio, parque, plaza o recinto donde ocurre el evento que se consulta. "
 "No infieras el lugar por el organizador. Si la imagen contiene varios actos "
 "con recintos distintos, o no se ve la fecha y el lugar inequívocos, "
 "devuelve one_event_single_venue=false, venue vacío. "
 "No completes un año ausente en el propio cartel."
)

def norm(value):
    text=unicodedata.normalize("NFKD",str(value or "").casefold())
    return re.sub(r"[^a-z0-9]+"," ","".join(c for c in text
                  if not unicodedata.combining(c))).strip()

def allowed_event(url):
    try:
        u=urlsplit(url)
        return u.scheme=="https" and u.hostname==HOST and u.port in (None,443) and u.username is None and u.password is None and not u.query and not u.fragment and bool(EVENT_PATH.fullmatch(u.path))
    except (ValueError,TypeError):
        return False

def allowed_image(url):
    try:
        u=urlsplit(url)
        return u.scheme=="https" and u.hostname==HOST and u.port in (None,443) and u.username is None and u.password is None and not u.query and not u.fragment and bool(IMAGE_PATH.fullmatch(u.path))
    except (ValueError,TypeError):
        return False

def source_policy(session):
    r=session.get(BASE+"/robots.txt",headers={"User-Agent":AGENT},timeout=12,allow_redirects=False)
    if r.status_code not in (200,404,410):
        raise RuntimeError("Official robots policy unavailable")
    rp=RobotFileParser()
    if r.status_code==200:
        rp.parse(r.text.splitlines())
    else:
        rp.allow_all=True
    return rp

def download_poster(session,url,robot):
    if not allowed_image(url) or not robot.can_fetch(AGENT,url):
        raise PermissionError("Poster URL outside source policy")
    r=session.get(url,headers=HEADERS,timeout=22,allow_redirects=False,stream=True)
    if r.status_code!=200:
        raise RuntimeError("Poster image HTTP "+str(r.status_code))
    raw=bytearray()
    for chunk in r.iter_content(65536):
        raw.extend(chunk)
        if len(raw)>MAX_IMAGE_BYTES:raise ValueError("Poster too large")
    blob=bytes(raw)
    if not blob.startswith((b"\xff\xd8\xff",b"\x89PNG\r\n\x1a\n",b"RIFF")):
        raise ValueError("Not a supported raster poster")
    im=Image.open(io.BytesIO(blob))
    if im.format not in ("JPEG","PNG","WEBP") or im.width<400 or im.height<400 or im.width*im.height>12_000_000:
        raise ValueError("Invalid poster dimensions or format")
    # The original hash, not a locally resized derivative, is the immutable proof.
    digest=hashlib.sha256(blob).hexdigest()
    if im.format=="JPEG":
        return digest,blob
    im=im.convert("RGB");im.thumbnail((1600,1600))
    b=io.BytesIO();im.save(b,format="JPEG",quality=82)
    return digest,b.getvalue()

def visible_date(text,event_day):
    """Confirm day/month printed in the image, independent of supplied metadata."""
    date=dt.date.fromisoformat(event_day[:10])
    value=norm(text)
    month=MONTHS[date.month-1]
    return bool(re.search(r"\b0?"+str(date.day)+r"\s+(?:de\s+)?"+month+r"\b",value)
                or re.search(r"\b0?"+str(date.day)+r"[./ -]0?"+str(date.month)+r"\b",value))

def check_reading(payload,event):
    if not isinstance(payload,dict) or payload.get("one_event_single_venue") is not True:
        return ""
    title=norm(payload.get("poster_title"))
    expected=norm(event["title"])
    if len(expected)<7 or expected not in title or not visible_date(payload.get("date_text",""),event["start"]):
        return ""
    venue=" ".join(str(payload.get("venue") or "").split())[:120]
    if not venue_quality.named_venue({"venue":venue,"municipality":event["municipality"]}):
        return ""
    # A short exact visual quote is required independently of normalized output.
    excerpt=norm(payload.get("venue_evidence"))
    if not norm(venue) in excerpt or len(excerpt)>190:
        return ""
    return venue

def agreement(first,second,event):
    a=check_reading(first,event);b=check_reading(second,event)
    return a if a and b and norm(a)==norm(b) else ""

def vision_call(session,image,model,api_key,event,second=False):
    payload={
        "model":model,"store":False,
        "instructions":SECOND_PROMPT if second else PROMPT,
        "input":[{"role":"user","content":[
            {"type":"input_text","text":"Verifica en el cartel el evento titulado "+
             str(event["title"])[:150]+" para el día "+event["start"][:10]+
             " del municipio "+str(event["municipality"])[:100]+
             ". IMPORTANTE: este contexto no demuestra que el lugar figure en la imagen."},
            {"type":"input_image","image_url":"data:image/jpeg;base64,"+
             base64.b64encode(image).decode("ascii"),"detail":"high"}
        ]}],
        "text":{"format":{"type":"json_schema","name":"event_poster_venue",
                          "strict":True,"schema":SCHEMA}},
        "max_output_tokens":850
    }
    reply=session.post("https://api.openai.com/v1/responses",headers={
            "Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
            json=payload,timeout=95)
    if reply.status_code!=200:raise RuntimeError("Visual model HTTP "+str(reply.status_code))
    data=reply.json()
    if data.get("status")!="completed":raise ValueError("Visual model incomplete")
    out="".join(z.get("text","") for m in data.get("output",[])
                 for z in m.get("content",[]) if z.get("type")=="output_text")
    if not out:raise ValueError("Empty vision output")
    return json.loads(out),data.get("usage",{})

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    tmp.replace(path)

def load(path,default):
    try:return json.loads(path.read_text(encoding="utf8"))
    except (OSError,ValueError):return default

def enrich(conn,now,today,*,session=None,api_key=None,max_posters=MAX_POSTERS_PER_RUN,
           max_api_calls=MAX_API_CALLS,max_cost_usd=MAX_COST_USD):
    client=session or requests.Session()
    key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY","")
    old=load(CACHE,{"version":VERSION,"posters":{}})
    entries=old.get("posters",{}) if old.get("version")==VERSION else {}
    counters={"checked":0,"manual_verified":0,"vision_verified":0,"rejected":0,
              "api_calls":0,"usage_usd":0.0,"deferred":0,"errors":[]}
    rows=[dict(r) for r in conn.execute(
         """SELECT id,title,start,"end",municipality,venue,image_url,source_url
            FROM events WHERE status='approved' AND
            substr(COALESCE("end",start),1,10)>=?""",(today.isoformat(),))]
    rows=[r for r in rows if not venue_quality.named_venue(r) and
          allowed_event(r.get("source_url","")) and allowed_image(r.get("image_url",""))]
    # User-confirmed posters first. Then prioritize images not already
    # reviewed; a poster with no place must not monopolize all future runs.
    rows.sort(key=lambda x:(x["source_url"] not in MANUALLY_VERIFIED,
                 entries.get(x["source_url"],{}).get("status") in (
                     "reviewed_no_single_venue","model_error"),
                 abs((dt.date.fromisoformat(x["start"][:10])-today).days),x["id"]))
    if not rows:
        atomic(REPORT,{"checked_at":now,**counters})
        return counters
    try:
        policy=source_policy(client)
    except (PermissionError,RuntimeError,requests.RequestException) as exc:
        counters["errors"].append({"error_type":type(exc).__name__,"stage":"robots"})
        atomic(REPORT,{"checked_at":now,**counters})
        return counters
    selected=rows[:max_posters]
    counters["deferred"]=max(0,len(rows)-len(selected))
    for r in selected:
        try:
            sha,img=download_poster(client,r["image_url"],policy)
            counters["checked"]+=1
            cache_key=r["source_url"]
            cached=entries.get(cache_key,{})
            saved=(cached if cached.get("sha256")==sha
                   and cached.get("event_date")==r["start"][:10]
                   and cached.get("title")==r["title"] else {})
            manual=MANUALLY_VERIFIED.get(cache_key)
            verified=""
            method=""
            if (manual and manual["poster_sha256"]==sha
                and manual["poster_image_url"]==r["image_url"]
                and manual["title"]==r["title"]
                and manual["municipality"]==r["municipality"]
                and manual["start_day"]==r["start"][:10]):
                verified=manual["venue"];method="human_posted_poster"
            elif saved.get("verified") and saved.get("venue"):
                verified=saved["venue"];method="two_visual_passes_cached"
            elif (saved.get("status")=="reviewed_no_single_venue" or
                  saved.get("retry_on","9999-12-31")>today.isoformat() and saved.get("status")=="model_error"):
                continue
            elif not key or counters["api_calls"]+2>max_api_calls or counters["usage_usd"]>=max_cost_usd:
                counters["deferred"]+=1
                continue
            else:
                responses=[]
                for second in (False,True):
                    counters["api_calls"]+=1  # Failed calls can still incur charges.
                    try:
                        record,usage=vision_call(client,img,MODEL,key,r,second=second)
                        counters["usage_usd"]=round(
                          counters["usage_usd"]+response_usage_cost(usage),7)
                        responses.append(record)
                    except (ValueError,RuntimeError,requests.RequestException) as exc:
                        entries[cache_key]={"sha256":sha,"title":r["title"],
                           "event_date":r["start"][:10],
                           "status":"model_error",
                           "error_type":type(exc).__name__,
                           "retry_on":(today+dt.timedelta(days=2)).isoformat()}
                        atomic(CACHE,{"version":VERSION,"posters":entries})
                        raise
                    if counters["usage_usd"]>=max_cost_usd and not second:
                        break
                if len(responses)==2:
                    verified=agreement(*responses,r)
                    if verified:method="two_independent_visual_passes"
                    else:
                        counters["rejected"]+=1
                        entries[cache_key]={"sha256":sha,"title":r["title"],
                           "event_date":r["start"][:10],
                           "status":"reviewed_no_single_venue"}
                        atomic(CACHE,{"version":VERSION,"posters":entries})
            if verified and venue_quality.named_venue(
               {"venue":verified,"municipality":r["municipality"]}):
                conn.execute("UPDATE events SET venue=?,updated_at=? WHERE id=?",
                             (verified,now,r["id"]))
                entries[cache_key]={"sha256":sha,"title":r["title"],
                       "event_date":r["start"][:10],
                       "status":"verified","verified":True,"venue":verified,
                       "method":method,"confirmed_on":today.isoformat(),
                       "image_url":r["image_url"]}
                if method=="human_posted_poster":counters["manual_verified"]+=1
                else:counters["vision_verified"]+=1
                atomic(CACHE,{"version":VERSION,"posters":entries})
        except (ValueError,RuntimeError,PermissionError,requests.RequestException,OSError) as exc:
            counters["errors"].append({"event_id":r["id"],"error_type":type(exc).__name__})
    atomic(REPORT,{"checked_at":now,**counters})
    return counters
