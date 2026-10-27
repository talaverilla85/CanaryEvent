"""Scheduled, budget-limited Telde municipal PDF extraction pipeline.

Only official municipal PDFs from the indexed program list are eligible.
Try deterministic text extraction first. Unreadable/inadequate pages go to
OpenAI vision only when OPENAI_API_KEY is provisioned. Model outputs remain
pending review, never become a publicly visible event automatically.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import requests
from pypdf import PdfReader

import telde_pdf_vision as tv
import telde_pdf_verified as verified_gate

ROOT = Path(__file__).resolve().parents[1]
STATE = tv.WORK / "scan_state.json"
CACHE = tv.WORK / "vision_cache.json"
REVIEW = tv.WORK / "pending_review.json"
REPORT = tv.WORK / "auto_report.json"
VERIFIED = tv.WORK / "verified_events.json"
SECOND_PROMPT = (
 "Actúa como auditor independiente de un programa municipal escaneado. "
 "Vuelve a leer visualmente desde cero la página, sin asumir datos aportados por otras lecturas. "
 "Devuelve solo actos individuales que indiquen inequívocamente título, día, hora y recinto "
 "en la imagen. Si falta cualquiera de estos cuatro campos, no incluyas el acto. "
 "Usa literalmente la información de la página; no deduzcas año, lugar ni fecha de títulos. "
 "Cita una evidencia corta realmente visible para cada acto. "
 "Si es portada, agenda genérica o ilegible, devuelve events=[] y page_is_program=false."
)
VERSION = "text-fallback-vision-v1"
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
DATE_TIME = re.compile(
    r"(?P<day>\d{1,2})\s+de\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+(?P<year>20\d{2}))?[\s,.:;\-–]*(?P<time>(?:[01]?\d|2[0-3])[:.][0-5]\d)"
    r"(?:\s*(?:h|horas))?[\s,.:;\-–]+(?P<title>[^\n]{8,150})",
    re.IGNORECASE,
)

def normalize(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(x for x in s if not unicodedata.combining(x))

def text_candidates(text: str, year: int) -> list[dict]:
    """Require date, hour and named activity in a single, parseable line.

    Other layouts deliberately fall through to AI; no guessed event dates.
    """
    results = []
    for line in text.splitlines():
        for match in DATE_TIME.finditer(normalize(line)):
            g = match.groupdict()
            try:
                day = dt.date(int(g["year"] or year), MONTHS[g["month"]], int(g["day"]))
            except ValueError:
                continue
            hhmm = g["time"].replace(".", ":")
            title = line[match.start("title"):match.end("title")].strip(" -.:;,")
            # Date sections, generic headings and tiny fragments are not events.
            if len(title) < 9 or not re.search("[A-Za-zÁ-ú]", title):
                continue
            results.append({
                "title": title[:170],
                "date": day.isoformat(),
                "time": hhmm.zfill(5),
                "venue": None,
                "evidence": line.strip()[:320],
                "type": "otros",
            })
    return results

def verify_text_evidence(text: str, candidate: dict) -> bool:
    evidence = normalize(str(candidate.get("evidence") or "")).strip()
    body = normalize(text)
    # Literal evidence must actually occur in the PDF's native text.
    return len(evidence) >= 12 and evidence in body

def choose_recent(index: dict, today: dt.date, filename: str | None,
                  limit: int) -> list[dict]:
    if filename:
        return tv.select_programs(index, filename, 1)
    docs = index.get("programs", [])
    recent = []
    current = today.year * 12 + today.month
    for item in docs:
        if not isinstance(item, dict) or not item.get("pdf_url"):
            continue
        url = urlsplit(item["pdf_url"])
        m = re.match(r"/wp-content/uploads/(20\d{2})/(\d{2})/", url.path)
        if not m:
            continue
        age = current - (int(m.group(1)) * 12 + int(m.group(2)))
        if -1 <= age <= 2:
            recent.append(item)
    # Recently uploaded documents first, not all 34 archive PDFs.
    recent.sort(key=lambda e: urlsplit(e["pdf_url"]).path, reverse=True)
    return recent

def run(argv=None, *, session=None, today: dt.date | None = None):
    pa = argparse.ArgumentParser()
    pa.add_argument("--filename", help="Pilot a specific filename listed by Telde")
    pa.add_argument("--max-docs", type=int, default=2)
    pa.add_argument("--max-pages", type=int, default=3)
    pa.add_argument("--max-api-calls", type=int, default=3)
    pa.add_argument("--max-cost-usd", type=float, default=0.05)
    pa.add_argument("--api", action="store_true",
                    help="Allow billable Responses API calls if secret exists")
    args = pa.parse_args(argv)
    if not 1 <= args.max_docs <= 3 or not 1 <= args.max_pages <= 5:
        pa.error("max-docs must be <=3 and max-pages <=5")
    if not 1 <= args.max_api_calls <= 8 or not .02 <= args.max_cost_usd <= .5:
        pa.error("Invalid usage guard limits")
    now = today or dt.datetime.now(dt.timezone.utc).date()
    key = os.environ.get("OPENAI_API_KEY", "")
    api_enabled = args.api and bool(key)
    index = tv.load_json(tv.SOURCE, {})
    picks = choose_recent(index, now, args.filename, args.max_docs)
    sess = session or requests.Session()
    robots = tv.official_robots(sess) if picks else None
    cache = tv.load_json(CACHE, {})
    verified_events = {e["id"]: e for e in tv.load_json(VERIFIED, [])
                       if isinstance(e,dict) and e.get("id")}
    prior = {e["id"]: e for e in tv.load_json(REVIEW, [])
             if isinstance(e, dict) and e.get("id")}
    state = tv.load_json(STATE, {})
    report = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "mode": "api_fallback" if api_enabled else "offline_safe",
              "model": tv.MODEL, "api_key_configured": bool(key),
              "api_calls": 0, "usage_usd": 0.0,
              "docs": [], "pending_review_count": 0, "auto_verified_count": 0,
              "notes": "Only corroborated future acts with matching time and named venue enter the feed; other results stay in review."}
    processed_docs = 0
    for pick in picks:
        if processed_docs >= args.max_docs:
            break
        url = tv.verify_pdf_url(pick["pdf_url"], int(pick["year"]))
        uid = hashlib.sha256(url.encode()).hexdigest()[:16]
        checkpoint = state.get(uid, {})
        if not args.filename and checkpoint.get("complete", False):
            # Completed files can be rechecked on future weekly catalog audits.
            checked_at = checkpoint.get("checked_at", "")
            try:
                checked_day = dt.date.fromisoformat(checked_at)
            except ValueError:
                checked_day = dt.date.min
            if (now - checked_day).days < 7:
                continue
        processed_docs += 1

        file, sha, size = tv.download_pdf(sess, url, robots, tv.WORK / "pdf_cache")
        pdf = PdfReader(str(file), strict=False)
        if not 1 <= len(pdf.pages) <= tv.MAX_PAGE_COUNT:
            raise ValueError("Unexpected PDF page count")
        uid = hashlib.sha256(url.encode()).hexdigest()[:16]
        checkpoint = state.get(uid, {})
        if checkpoint.get("sha") != sha:
            checkpoint = {"sha": sha, "done_pages": []}
        done = set(int(n) for n in checkpoint.get("done_pages", []))
        doc = {"name": pick["title"], "pdf_url": url, "sha256": sha,
               "pages": len(pdf.pages), "bytes": size, "inspected": []}
        report["docs"].append(doc)
        # Continue after previously completed pages rather than charging twice.
        todo = [p for p in range(len(pdf.pages)) if p not in done]
        for i in todo[:args.max_pages]:
            page = pdf.pages[i]
            native = (page.extract_text() or "").strip()
            candidates = text_candidates(native, int(pick["year"]))
            method = "native_text" if candidates else "ai_vision" if len(native) < 150 else "ai_text"
            info = {"page": i + 1, "native_text_chars": len(native), "route": method}
            doc["inspected"].append(info)
            valid = []
            if candidates:
                for c in candidates:
                    if verify_text_evidence(native, c):
                        rec, err = tv.validate_candidate(
                            c, int(pick["year"]), pick["title"],
                            url, sha, i, now
                        )
                        if rec:
                            rec["extractor"] = "native_text"
                            valid.append(rec)
                # Only skip vision if deterministic extraction found coherent
                # activity records. Otherwise ask AI for the difficult layout.
                if not valid:
                    method = "ai_text" if len(native) >= 150 else "ai_vision"
                    info["route"] = method
            if not valid:
                cachekey = f"{sha}/{i}/{tv.MODEL}/{VERSION}/{method}"
                if cachekey in cache:
                    decoded = cache[cachekey]["output"]
                    info["status"] = "cached"
                elif not api_enabled:
                    info["status"] = "requires_openai_api_key"
                    continue
                elif report["api_calls"] >= args.max_api_calls or (
                    args.max_cost_usd - report["usage_usd"] < .01
                ):
                    info["status"] = "skipped_api_budget"
                    continue
                else:
                    if method == "ai_vision":
                        image, dims = tv.render_page_jpeg(file, i)
                        decoded, usage = tv.call_openai_vision(
                            image, int(pick["year"]), pick["title"],
                            tv.MODEL, key, sess
                        )
                        info["render_size"] = list(dims)
                    else:
                        decoded, usage = tv.call_openai_text(
                            native, int(pick["year"]), pick["title"],
                            tv.MODEL, key, sess
                        )
                    cost = tv.response_usage_cost(usage)
                    report["api_calls"] += 1
                    report["usage_usd"] = round(report["usage_usd"] + cost, 7)
                    cache[cachekey] = {"output": decoded, "usage": usage,
                                       "measured_cost_usd": cost}
                    tv.atomic_json(CACHE, cache)
                    info["status"] = "new_api_result"
                for c in decoded.get("events", []):
                    if not isinstance(c, dict):
                        continue
                    if method == "ai_text" and not verify_text_evidence(native, c):
                        continue
                    rec, err = tv.validate_candidate(
                        c, int(pick["year"]), pick["title"], url, sha, i, now
                    )
                    if rec:
                        rec["extractor"] = method
                        valid.append(rec)
            for rec in valid:
                prior[rec["id"]] = rec
            info["candidates_pending_review"] = len(valid)
            # OCR-free scan: original visual extraction AND independent second
            # visual pass must agree about title, date, time and named venue.
            can_finish=True
            if valid and method=="ai_vision":
                ck2=f"{sha}/{i}/{tv.MODEL}/{VERSION}/independent_double_read"
                if ck2 in cache:
                    second=cache[ck2]["output"]
                    info["verification"]="cached_independent_visual_read"
                elif not api_enabled or report["api_calls"]>=args.max_api_calls or (
                    args.max_cost_usd-report["usage_usd"]<.01
                ):
                    second=None
                    can_finish=False
                    info["verification"]="pending_second_read_budget"
                else:
                    img,_=tv.render_page_jpeg(file,i)
                    second,usage=tv.call_openai_vision(
                        img,int(pick["year"]),pick["title"],tv.MODEL,key,sess,
                        instructions=SECOND_PROMPT
                    )
                    cost=tv.response_usage_cost(usage)
                    report["api_calls"]+=1
                    report["usage_usd"]=round(report["usage_usd"]+cost,7)
                    cache[ck2]={"output":second,"usage":usage,"measured_cost_usd":cost}
                    tv.atomic_json(CACHE,cache)
                    info["verification"]="new_independent_visual_read"
                if second is not None:
                    if decoded.get("page_is_program") and second.get("page_is_program"):
                        matched=verified_gate.approved_candidates(
                            decoded.get("events",[]), second.get("events",[]),today=now
                        )
                    else:
                        matched=[]
                    for cand in matched:
                        rec,err=tv.validate_candidate(
                            cand,int(pick["year"]),pick["title"],url,sha,i,now
                        )
                        if rec and rec["id"] in prior:
                            rec["review_status"]="auto_verified"
                            rec["verification"]="two_independent_visual_passes"
                            rec["verified_at"]=now.isoformat()
                            verified_events[rec["id"]]=rec
                    info["auto_verified"]=len(matched)
            if can_finish:done.add(i)
        checkpoint["done_pages"] = sorted(done)
        checkpoint["complete"] = len(done) == len(pdf.pages)
        checkpoint["checked_at"] = now.isoformat()
        state[uid] = checkpoint
    report["pending_review_count"] = len(prior)
    report["auto_verified_count"] = len(verified_events)
    tv.atomic_json(REVIEW, sorted(prior.values(), key=lambda x: (x["date"], x["id"])))
    tv.atomic_json(VERIFIED,sorted(verified_events.values(),key=lambda x:(x["date"],x["id"])))
    tv.atomic_json(STATE, state)
    tv.atomic_json(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report

if __name__ == "__main__":
    try:
        run()
    except (ValueError, RuntimeError, PermissionError, requests.RequestException) as exc:
        print("TELDE PDF AUTO ERROR:", type(exc).__name__, str(exc)[:250], file=sys.stderr)
        sys.exit(2)
