#!/usr/bin/env python3
"""Read Telde municipality's PDF programmes into a REVIEW queue, never events.json.

Examples:
  python scripts/telde_pdf_vision.py --filename sanfrancisco26.pdf --max-pages 1
  python scripts/telde_pdf_vision.py --filename sanfrancisco26.pdf --max-pages 1 --api

--api requires OPENAI_API_KEY and makes billable Responses API calls.
No model output is published automatically; approve candidates separately.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"public"/"municipal_programs.json"
WORK=ROOT/"data"/"telde_pdf_pilot"
CACHE=WORK/"vision_cache.json"
REVIEW=WORK/"pending_review.json"
REPORT=WORK/"pilot_report.json"
USER_AGENT="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
MODEL="gpt-6-luna"
PROMPT_VERSION="telde-program-v1"
# Standard token prices, USD/1M. See OpenAI model pricing; subject to change.
RATES={MODEL:{"input":0.10,"cached_input":0.01,"output":0.50}}
MAX_PDF_BYTES=8_000_000
MAX_PAGE_COUNT=35
MAX_IMG_PX=1900
REQUEST_MAX_OUTPUT=1800

SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{
  "events":{
   "type":"array",
   "items":{"type":"object","additionalProperties":False,
    "properties":{
     "title":{"type":"string"},
     "date":{"type":["string","null"]},
     "time":{"type":["string","null"]},
     "venue":{"type":["string","null"]},
     "evidence":{"type":"string"},
     "type":{"type":"string","enum":["fiesta","musica","gastronomia","familia","deporte","religioso","cultura","otros"]},
    },
    "required":["title","date","time","venue","evidence","type"]
   }
  },
  "page_is_program":{"type":"boolean"}
 },
 "required":["events","page_is_program"]
}
SYSTEM_PROMPT=(
 "Eres un extractor documental estricto de programas municipales de Telde, Gran Canaria. "
 "Devuelve SOLO actividades individuales que se puedan leer realmente en esta página. "
 "No uses conocimientos externos ni conviertas la portada, títulos genéricos o los días de "
 "una fiesta en eventos inventados. Cada evento requiere una actividad concreta y fecha "
 "explícita, salvo si el propio programa indica el año en portada; entonces puedes usar "
 "el año de la fuente oficial suministrada. Conserva fielmente los nombres propios, "
 "horarios y recintos. Cuando no se vea hora/recinto/fecha, usa null. "
 "No inventes precio ni acceso gratuito. Evidence debe ser una cita breve, LITERAL y "
 "visible de la página, donde conste al menos la actividad y el día. "
 "Si la página es portada o ilegible, events=[]; page_is_program=false."
)

def atomic_json(path:Path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix(path.suffix+".tmp")
 temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 temp.replace(path)

def load_json(path:Path, fallback):
 if not path.exists():return fallback
 return json.loads(path.read_text(encoding="utf8"))

def select_programs(index,filename:str|None,limit:int):
 entries=[e for e in index.get("programs",[]) if isinstance(e,dict) and e.get("pdf_url")]
 if filename:
  chosen=[e for e in entries if urlsplit(e["pdf_url"]).path.rsplit("/",1)[-1]==filename]
  if not chosen:raise ValueError("PDF not found in official Telde index: "+filename)
  return chosen[:limit]
 # Most recently uploaded first; old archives are deliberately not bulk-extracted.
 return sorted(entries,key=lambda e:e["pdf_url"],reverse=True)[:limit]

def verify_pdf_url(url:str,year:int):
 uri=urlsplit(url)
 if uri.scheme!="https" or uri.hostname!="www.telde.es" or uri.query or uri.fragment:
  raise ValueError("PDF outside allowed official origin")
 if not re.fullmatch(r"/wp-content/uploads/"+str(year)+r"/\d{2}/[a-zA-Z0-9_.-]+\.pdf",uri.path):
  raise ValueError("PDF outside allowed Telde upload directory")
 return url

def official_robots(session):
 r=session.get("https://www.telde.es/robots.txt",
               headers={"User-Agent":USER_AGENT},timeout=15,allow_redirects=False)
 if r.status_code!=200:
  raise RuntimeError("Telde robots policy unavailable HTTP "+str(r.status_code))
 rule=RobotFileParser();rule.parse(r.text.splitlines())
 return rule

def download_pdf(session,url,robots,cache_dir):
 if not robots.can_fetch(USER_AGENT,url):
  raise PermissionError("Telde robots policy blocks this PDF")
 # PDF bytes are cached locally, but the source index itself remains the
 # authority; re-download when explicitly running a new extraction pilot.
 r=session.get(url,headers={"User-Agent":USER_AGENT,"Accept":"application/pdf"},
               timeout=35,allow_redirects=False,stream=True)
 if r.status_code!=200:
  raise RuntimeError("PDF HTTP "+str(r.status_code))
 if "pdf" not in r.headers.get("Content-Type","").lower():
  raise ValueError("Server did not return a PDF")
 chunks=bytearray()
 for chunk in r.iter_content(64*1024):
  chunks.extend(chunk)
  if len(chunks)>MAX_PDF_BYTES:raise ValueError("PDF exceeds size limit")
 raw=bytes(chunks)
 if not raw.startswith(b"%PDF"):raise ValueError("Invalid PDF header")
 sha=hashlib.sha256(raw).hexdigest()
 cache_dir.mkdir(parents=True,exist_ok=True)
 p=cache_dir/(sha+".pdf")
 if not p.exists():p.write_bytes(raw)
 return p,sha,len(raw)

def pdf_pages(pdf_path):
 pdf=PdfReader(str(pdf_path),strict=False)
 if not pdf.pages or len(pdf.pages)>MAX_PAGE_COUNT:
  raise ValueError("Unexpected PDF page count")
 lengths=[]
 for page in pdf.pages:
  text=(page.extract_text() or "").strip()
  lengths.append(len(text))
 return lengths

def render_page_jpeg(pdf_path,index):
 """Native PDF rendering, not OCR; image pixels go to a vision model."""
 import pypdfium2 as pdfium
 from PIL import Image
 pdf=pdfium.PdfDocument(str(pdf_path))
 try:
  page=pdf[index]
  w,h=page.get_size()
  scale=min(MAX_IMG_PX/max(w,h),2.2)
  image=page.render(scale=scale).to_pil().convert("RGB")
  image.thumbnail((MAX_IMG_PX,MAX_IMG_PX),Image.Resampling.LANCZOS)
  buf=io.BytesIO();image.save(buf,"JPEG",quality=82,optimize=True)
  return buf.getvalue(),image.size
 finally:
  pdf.close()

def response_usage_cost(usage:dict,model=MODEL):
 rate=RATES[model]
 inp=int(usage.get("input_tokens",0))
 out=int(usage.get("output_tokens",0))
 details=usage.get("input_tokens_details") or {}
 cached=min(inp,int(details.get("cached_tokens",0)))
 cost=(inp-cached)*rate["input"]/1e6+cached*rate["cached_input"]/1e6+out*rate["output"]/1e6
 return round(cost,7)

def call_openai_text(page_text,year,title,model,key,session):
    """Read existing text before using paid visual decoding.

    Structured JSON and no-store prevent unintended retention or extra calls.
    The caller independently confirms that each evidence quote occurs in text.
    """
    payload={
      "model":model,
      "store":False,
      "instructions":SYSTEM_PROMPT,
      "input":[{"role":"user","content":[{
         "type":"input_text","text":
          f"Programa municipal de Telde, fuente {title}, año {year}. "
          f"Extrae las actividades con fecha explícita de este texto:\\n{page_text[:14500]}"
      }]}],
      "text":{"format":{"type":"json_schema","name":"telde_pdf_events",
                         "strict":True,"schema":SCHEMA}},
      "max_output_tokens":REQUEST_MAX_OUTPUT,
    }
    response=session.post("https://api.openai.com/v1/responses",
      headers={"Authorization":"Bearer "+key,
               "Content-Type":"application/json"},
      json=payload,timeout=110)
    if response.status_code!=200:
       raise RuntimeError("OpenAI API HTTP "+str(response.status_code)+": "+
          str((response.json().get("error") or {}).get("type","request_failed"))[:80])
    reply=response.json()
    if reply.get("status")!="completed":
       raise ValueError("Model response incomplete")
    content="".join(item.get("text","")
      for msg in reply.get("output",[]) if msg.get("type")=="message"
      for item in msg.get("content",[]) if item.get("type")=="output_text")
    if not content:
       raise ValueError("Model returned no structured text")
    parsed=json.loads(content)
    if not isinstance(parsed,dict) or not isinstance(parsed.get("events"),list):
       raise ValueError("Model response is not an event document")
    return parsed,reply.get("usage",{})


def call_openai_vision(image_bytes,year,title,model,key,session):
 payload={
  "model":model,
  "store":False,
  "instructions":SYSTEM_PROMPT,
  "input":[{
   "role":"user","content":[
    {"type":"input_text","text":f"Fuente oficial municipal: {title}. Año {year}. Extrae cada actividad fechada que se lea EN ESTA página. JSON."},
    {"type":"input_image","image_url":"data:image/jpeg;base64,"+base64.b64encode(image_bytes).decode("ascii"),
     "detail":"high"}]
  }],
  "text":{"format":{"type":"json_schema","name":"telde_pdf_events","strict":True,"schema":SCHEMA}},
  "max_output_tokens":REQUEST_MAX_OUTPUT,
 }
 response=session.post("https://api.openai.com/v1/responses",
   headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
   json=payload,timeout=110)
 # No retry after an unknown response; never risk duplicate charges.
 if response.status_code!=200:
  raise RuntimeError("OpenAI API HTTP "+str(response.status_code)+": "+
      str((response.json().get("error") or {}).get("type","request_failed"))[:80])
 reply=response.json()
 if reply.get("status")!="completed":
  raise ValueError("Model response incomplete or pending; no invented output")
 text="".join(part.get("text","")
   for o in reply.get("output",[]) if o.get("type")=="message"
   for part in o.get("content",[]) if part.get("type")=="output_text")
 if not text:raise ValueError("Model did not return a text answer")
 decoded=json.loads(text)
 if not isinstance(decoded,dict) or not isinstance(decoded.get("events"),list):
  raise ValueError("Model failed required JSON structure")
 return decoded,reply.get("usage",{})

def validate_candidate(rec,year,title,url,sha,page,now):
 """Never publish from model output: create only a pending review record."""
 date=str(rec.get("date") or "").strip()
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):return None,"missing_or_invalid_date"
 try:day=dt.date.fromisoformat(date)
 except ValueError:return None,"impossible_date"
 if day.year!=year:return None,"date_year_differs_from_official_index"
 name=" ".join(str(rec.get("title") or "").split())
 if len(name)<7 or len(name)>170:return None,"invalid_title"
 evidence=" ".join(str(rec.get("evidence") or "").split())
 if len(evidence)<12:return None,"insufficient_literal_evidence"
 time=str(rec.get("time") or "").strip()
 if time:
  if not re.fullmatch(r"\d{2}:\d{2}",time):return None,"bad_time"
  hh,mm=map(int,time.split(":"))
  if hh>23 or mm>59:return None,"impossible_time"
 place=" ".join(str(rec.get("venue") or "").split())[:145]
 category=rec.get("type")
 if category not in {"fiesta","musica","gastronomia","familia","deporte","religioso","cultura","otros"}:
  return None,"invalid_type"
 uid=hashlib.sha256((url+"|"+date+"|"+name.casefold()+"|"+time).encode()).hexdigest()[:16]
 return {
  "id":"telde-pdf-"+uid,"title":name,"date":date,"time":time or None,
  "venue":place or None,"type":category,"evidence":evidence[:320],
  "municipality":"Telde","program_title":title,"pdf_url":url,
  "pdf_sha256":sha,"pdf_page":page+1,"review_status":"pending_review",
  "date_state":"expired" if day<now else "upcoming",
  "note":"NO PUBLICAR sin contrastar fecha/horario con la página escaneada",
 },None

def run(argv=None, session=None):
 pa=argparse.ArgumentParser(description="Telde PDF vision pilot: safe and review-only")
 pa.add_argument("--filename",help="Exact PDF basename from Telde's approved inventory")
 pa.add_argument("--limit",type=int,default=1)
 pa.add_argument("--max-pages",type=int,default=2)
 pa.add_argument("--max-cost-usd",type=float,default=0.05)
 pa.add_argument("--model",default=MODEL,choices=list(RATES))
 pa.add_argument("--api",action="store_true",help="Explicitly enable billable API calls")
 args=pa.parse_args(argv)
 if not 1<=args.limit<=3 or not 1<=args.max_pages<=5 or not .02<=args.max_cost_usd<=1:
  pa.error("Pilot caps: limit<=3, max-pages<=5, 0.02<=max-cost-usd<=1")
 key=os.environ.get("OPENAI_API_KEY","")
 if args.api and not key:raise RuntimeError("Set OPENAI_API_KEY before enabling --api (no key on disk)")
 index=load_json(SOURCE,{})
 picks=select_programs(index,args.filename,args.limit)
 client=session or requests.Session()
 policies=official_robots(client)
 cache=load_json(CACHE,{})
 seen={x["id"]:x for x in load_json(REVIEW,[]) if isinstance(x,dict) and x.get("id")}
 report={"created_at":dt.datetime.now(dt.timezone.utc).isoformat(),
   "source_url":index.get("source_url"),
   "mode":"api_review_only" if args.api else "safe_dry_run",
   "model":args.model,"max_cost_usd":args.max_cost_usd,
   "actual_api_calls":0,"actual_input_tokens":0,"actual_output_tokens":0,
   "measured_cost_usd":0.0,"documents":[]}
 today=dt.datetime.now(dt.timezone(dt.timedelta(0))).date()
 for pick in picks:
  year=int(pick["year"]);url=verify_pdf_url(pick["pdf_url"],year)
  target_url=urlsplit(url).path.rsplit("/",1)[-1]
  doc={"title":pick["title"],"pdf_url":url,"pages":[]}
  report["documents"].append(doc)
  pdf_path=None
  pdf_path,sha,length=download_pdf(client,url,policies,WORK/"pdf_cache")
  sizes=pdf_pages(pdf_path)
  doc.update(pdf_sha256=sha,pdf_bytes=length,page_count=len(sizes),
             searchable_page_count=sum(x>=150 for x in sizes))
  for page in range(min(args.max_pages,len(sizes))):
   mode="text_searchable" if sizes[page]>=150 else "vision_required"
   info={"page":page+1,"pdf_text_chars":sizes[page],"format":mode,
         "status":"inspected_no_api" if not args.api else "pending"}
   doc["pages"].append(info)
   if not args.api:continue
   ck=f"{sha}/{page}/{args.model}/{PROMPT_VERSION}"
   if ck in cache:
    decoded=cache[ck]["output"]
    info.update(status="cached_response",cache_hit=True)
   else:
    # Soft budget: do not start a new page if remaining limit is too small.
    if args.max_cost_usd-report["measured_cost_usd"]<0.015:
     info["status"]="skipped_budget_guard";continue
    image,size=render_page_jpeg(pdf_path,page)
    info["render_size"]=list(size)
    decoded,usage=call_openai_vision(image,year,pick["title"],args.model,key,client)
    cost=response_usage_cost(usage,args.model)
    report["actual_api_calls"]+=1
    report["actual_input_tokens"]+=int(usage.get("input_tokens",0))
    report["actual_output_tokens"]+=int(usage.get("output_tokens",0))
    report["measured_cost_usd"]=round(report["measured_cost_usd"]+cost,7)
    info.update(status="api_extracted_review_required",
                measured_cost_usd=cost,cache_hit=False)
    cache[ck]={"output":decoded,"usage":usage,"cost_usd":cost,"page":page+1,
               "pdf_url":url,"model":args.model}
    atomic_json(CACHE,cache)
   accepted=rejected=0
   rejected_reasons={}
   for raw in decoded.get("events",[]):
    if not isinstance(raw,dict):continue
    entry,error=validate_candidate(raw,year,pick["title"],url,sha,page,today)
    if error:
     rejected+=1
     rejected_reasons[error]=rejected_reasons.get(error,0)+1
    else:seen[entry["id"]]=entry;accepted+=1
   info.update(candidates_pending_review=accepted,rejected_by_validator=rejected,validator_rejection_reasons=rejected_reasons)
 atomic_json(REVIEW,list(seen.values()))
 atomic_json(REPORT,report)
 print(json.dumps(report,ensure_ascii=False,indent=2))
 return report

if __name__=="__main__":
 try:run()
 except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
  print("PILOT ERROR:",type(exc).__name__,str(exc)[:200],file=sys.stderr)
  sys.exit(2)
