"""Generic, allowlisted municipal festival PDF visual extraction.

Starts with Santa LucÃ­a, AgÃ¼imes and GÃ¡ldar official PDF programmes.
It reuses Telde's page renderer, Responses API JSON schema, two independent
visual readings, usage safeguards and evidence gate; there is no blind publish.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

import requests
from pypdf import PdfReader
import telde_pdf_vision as vision
import telde_pdf_verified as gate
import telde_pdf_auto as telde
import telde_pdf_priority as priority
import municipal_pdf_sources as sources

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/"data"/"municipal_pdf_pilot"
INDEX=ROOT/"public"/"municipal_pdf_programs.json"
REVIEW=WORK/"pending_review.json"
VERIFIED=WORK/"verified_events.json"
ARCHIVE=WORK/"expired_archive.json"
CACHE=WORK/"vision_cache.json"
STATE=WORK/"scan_state.json"
REPORT=WORK/"auto_report.json"
VERSION="text-fallback-vision-v3"
MONTH_RE=r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
DATE_RE=re.compile(r"(?<!\d)(\d{1,2})\s+(?:de\s+)?("+MONTH_RE+r")(?!\w)",re.I)
TIME_RE=re.compile(r"(?:[01]?\d|2[0-3])[:.][0-5]\d\s*(?:h\b)?",re.I)
def page_scores(pdf: PdfReader,year: int,today: dt.date):
    """Rank document pages with explicit future dates; never infer per-event dates."""
    page_info=[]
    for i,page in enumerate(pdf.pages):
        text=(page.extract_text() or "").strip()
        days=[]
        for match in DATE_RE.finditer(text):
            month=telde.MONTHS.get(telde.normalize(match.group(2)))
            try:
                when=dt.date(year,month,int(match.group(1)))
            except (ValueError,TypeError):
                continue
            if today<=when<=today+dt.timedelta(days=120):
                days.append(when)
        future=bool(days)
        times=len(TIME_RE.findall(text))
        # Pages with near-future explicit days and event hours first.
        score=3 if future and times else 2 if future else 1 if times else 0
        page_info.append((i,text,score,min(days) if days else None))
    return sorted(page_info,key=lambda e:(-e[2],e[3] or dt.date.max,e[0]))

def candidates(index,today,state):
    docs=[]
    for entry in index.get("programs",[]):
        m=entry.get("municipality")
        year=entry.get("year")
        url=entry.get("pdf_url")
        if m not in sources.SOURCES or type(year)!=int or not url:
            continue
        if not sources.verified_pdf(url,m,year):
            continue
        if year!=today.year:
            continue
        # End hints are sourced from a reviewed cover of the exact official PDF.
        # Such programmes remain in inventory, but not in paid extraction.
        end=(priority.day_of(entry.get("program_end_hint"))
             if entry.get("program_end_evidence_url")==url else None)
        if end and end<today:
            continue
        age=priority.upload_age_months(url,today)
        if age is None or not (-1<=age<=2 or (end and end>=today)):
            continue
        ck=state.get(priority.doc_id(url),{})
        # Completed documents are not read again until their URL changes; the
        # periodically refreshed inventory can reveal the next year's PDF.
        if ck.get("complete"):
            continue
        if priority.pause_active(ck,today):
            continue
        future_hint=bool(end and end>=today)
        docs.append((0 if future_hint else 1,age,url,entry))
    docs.sort(key=lambda row:(row[0],row[1],row[2]))
    return [r[3] for r in docs]

def run(argv=None,*,today=None,session=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--api",action="store_true")
    ap.add_argument("--archive-only",action="store_true")
    ap.add_argument("--max-docs",type=int,default=1)
    ap.add_argument("--max-pages",type=int,default=3)
    ap.add_argument("--max-api-calls",type=int,default=4)
    ap.add_argument("--max-cost-usd",type=float,default=.05)
    args=ap.parse_args(argv)
    if not(1<=args.max_docs<=3 and 1<=args.max_pages<=5 and
           1<=args.max_api_calls<=8 and .02<=args.max_cost_usd<=.5):
        ap.error("Invalid PDF workload or budget limits")
    today=today or dt.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    key=os.getenv("OPENAI_API_KEY","")
    api=bool(args.api and key)
    sess=session or requests.Session()
    index=vision.load_json(INDEX,{})
    state=vision.load_json(STATE,{})
    cache=vision.load_json(CACHE,{})
    pending={e["id"]:e for e in vision.load_json(REVIEW,[]) if isinstance(e,dict) and e.get("id")}
    verified={e["id"]:e for e in vision.load_json(VERIFIED,[]) if isinstance(e,dict) and e.get("id")}
    history={"|".join((e["id"],e.get("pdf_sha256",""),e.get("archived_from","pending_review"))):e
             for e in vision.load_json(ARCHIVE,[]) if isinstance(e,dict) and e.get("id")}
    archived=telda_archive(today,pending,verified,history)
    report={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "mode":"archive_only" if args.archive_only else "api" if api else "offline",
            "model":vision.MODEL,"api_calls":0,"usage_usd":0.,
            "documents":[],"errors":[],"deferred":[],"archived_this_run":archived}
    docs=[] if args.archive_only else candidates(index,today,state)
    for entry in docs:
        if len(report["documents"])>=args.max_docs:
            break
        url=entry["pdf_url"]
        municipality=entry["municipality"]
        year=entry["year"]
        uid=priority.doc_id(url)
        try:
            robots=sources.robots_for(sess,sources.SOURCES[municipality]["host"])
            file,sha,size=vision.download_pdf(sess,url,robots,WORK/"pdf_cache",max_bytes=12_000_000)
            pdf=PdfReader(str(file),strict=False)
            if not(1<=len(pdf.pages)<=vision.MAX_PAGE_COUNT):
                raise ValueError("Unexpected PDF page count")
            checkpoint=state.get(uid,{})
            if checkpoint.get("sha")!=sha:
                checkpoint={"sha":sha,"done_pages":[]}
                for c in (pending,verified):
                    for k,record in list(c.items()):
                        if record.get("pdf_url")==url and record.get("pdf_sha256")!=sha:
                            del c[k]
            done=set(checkpoint.get("done_pages",[]))
            pages=[e for e in page_scores(pdf,year,today) if e[0] not in done]
            report_doc={"municipality":municipality,"pdf_url":url,
                        "pdf_sha256":sha,"pages":len(pdf.pages),
                        "bytes":size,"inspected":[]}
            report["documents"].append(report_doc)
            for i,native,score,_ in pages[:args.max_pages]:
                info={"page":i+1,"native_text_chars":len(native),
                      "page_priority":score}
                report_doc["inspected"].append(info)
                first_key=f"{sha}/{i}/{vision.MODEL}/{VERSION}/ai_vision"
                second_key=f"{sha}/{i}/{vision.MODEL}/{VERSION}/independent_double_read"
                try:
                    if first_key in cache:
                        first=cache[first_key]["output"]
                        info["first_read"]="cached"
                    elif not api:
                        info["first_read"]="requires_key"
                        continue
                    elif not budget_ok(report,args):
                        info["first_read"]="budget"
                        continue
                    else:
                        image,_=vision.render_page_jpeg(file,i)
                        first,usage=vision.call_openai_vision(
                            image,year,entry["title"],vision.MODEL,key,sess,
                            municipality=municipality)
                        charge(report,usage)
                        cache[first_key]={"output":first,"usage":usage}
                        vision.atomic_json(CACHE,cache)
                        info["first_read"]="ai_vision"
                    accepted=[]
                    for item in first.get("events",[]):
                        if not isinstance(item,dict):
                            continue
                        record,err=vision.validate_candidate(
                            item,year,entry["title"],url,sha,i,today,
                            municipality=municipality)
                        if record:
                            record["extractor"]="ai_vision"
                            if record["date_state"]=="expired":
                                archived+=int(telda_archive_one(record,history,today))
                            else:
                                pending[record["id"]]=record
                                accepted.append(record)
                    info["candidates_for_review"]=len(accepted)
                    complete=True
                    if accepted:
                        if second_key in cache:
                            second=cache[second_key]["output"]
                            info["second_read"]="cached"
                        elif not api or not budget_ok(report,args):
                            complete=False
                            second=None
                            info["second_read"]="budget_or_key"
                        else:
                            image,_=vision.render_page_jpeg(file,i)
                            second,usage=vision.call_openai_vision(
                                image,year,entry["title"],vision.MODEL,key,sess,
                                instructions=telda_second_prompt(),municipality=municipality)
                            charge(report,usage)
                            cache[second_key]={"output":second,"usage":usage}
                            vision.atomic_json(CACHE,cache)
                            info["second_read"]="independent_vision"
                        if second is not None:
                            if first.get("page_is_program") and second.get("page_is_program"):
                                matches=gate.approved_candidates(first["events"],second["events"],today=today)
                            else:
                                matches=[]
                            for item in matches:
                                rec,err=vision.validate_candidate(
                                    item,year,entry["title"],url,sha,i,today,
                                    municipality=municipality)
                                if rec and rec["id"] in pending:
                                    rec["extractor"]="ai_vision"
                                    rec["review_status"]="auto_verified"
                                    rec["verification"]="two_independent_visual_passes"
                                    rec["verified_at"]=today.isoformat()
                                    verified[rec["id"]]=rec
                            info["auto_verified"]=len(matches)
                    if complete:
                        done.add(i)
                except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
                    info["error_type"]=type(exc).__name__
                    report["errors"].append({
                        "municipality":municipality,"pdf_url":url,
                        "pdf_page":i+1,"error_type":type(exc).__name__})
                    # Other pages and the already-verified acts remain intact.
                finally:
                    # A per-page commit is vital: a later model failure must
                    # never erase the source-proof checkpoint from earlier pages.
                    checkpoint["sha"]=sha
                    checkpoint["done_pages"]=sorted(done)
                    checkpoint["complete"]=len(done)==len(pdf.pages)
                    checkpoint["checked_at"]=today.isoformat()
                    state[uid]=checkpoint
                    vision.atomic_json(STATE,state)
                    vision.atomic_json(REVIEW,sorted(pending.values(),key=lambda r:(r["date"],r["id"])))
                    vision.atomic_json(VERIFIED,sorted(verified.values(),key=lambda r:(r["date"],r["id"])))
                    vision.atomic_json(ARCHIVE,sorted(history.values(),key=lambda r:(r.get("date",""),r["id"])))
            checkpoint["sha"]=sha
            checkpoint["done_pages"]=sorted(done)
            checkpoint["complete"]=len(done)==len(pdf.pages)
            checkpoint["checked_at"]=today.isoformat()
            state[uid]=checkpoint
        except (ValueError,RuntimeError,PermissionError,requests.RequestException) as exc:
            report["errors"].append({"municipality":municipality,"pdf_url":url,
                                     "error_type":type(exc).__name__})
    report["archived_this_run"]=archived
    report["pending_review_count"]=len(pending)
    report["auto_verified_count"]=len(verified)
    report["archived_count"]=len(history)
    for path,records in ((REVIEW,pending),(VERIFIED,verified),(ARCHIVE,history)):
        vision.atomic_json(path,sorted(records.values(),key=lambda e:(e.get("date",""),e["id"])))
    vision.atomic_json(STATE,state)
    vision.atomic_json(REPORT,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def telda_archive_one(record,history,today):
    key="|".join((record["id"],record.get("pdf_sha256",""),"pending_review"))
    if key in history:
        return False
    history[key]={**record,"date_state":"expired","review_status":"archived",
                  "archived_from":"pending_review","archived_on":today.isoformat()}
    return True

def telda_archive(today,pending,verified,history):
    count=0
    for label,items in (("pending_review",pending),("auto_verified",verified)):
        for item_id,record in list(items.items()):
            day=priority.day_of(record.get("date"))
            if day and day<today:
                key="|".join((record["id"],record.get("pdf_sha256",""),label))
                if key not in history:
                    history[key]={**record,"date_state":"expired","review_status":"archived",
                                  "archived_from":label,"archived_on":today.isoformat()}
                    count+=1
                del items[item_id]
    return count

def budget_ok(report,args):
    return (report["api_calls"]<args.max_api_calls
            and args.max_cost_usd-report["usage_usd"]>=.01)

def charge(report,usage):
    report["api_calls"]+=1
    report["usage_usd"]=round(report["usage_usd"]+vision.response_usage_cost(usage),7)

def telda_second_prompt():
    return telde.SECOND_PROMPT

if __name__=="__main__":
    run()
