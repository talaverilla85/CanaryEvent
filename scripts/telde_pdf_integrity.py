"""Safe ingestion gate for actual scanned Telde PDFs.

A "verified_events.json" row is not enough to publish an event. Require
the actual document hash from the official download scan state and *both*
independent Responses API caches that attest the same date, time, title and
venue on the same page. Test/demo records cannot pass this gate.
"""
import datetime as dt
import hashlib
import re

import telde_pdf_verified as gate

def _record_matches(reference, candidate):
    if not isinstance(candidate,dict):
        return False
    return all(
        gate.norm(reference.get(k))==gate.norm(candidate.get(k))
        for k in ("title","date","time","venue")
    ) and len(str(candidate.get("evidence") or ""))>=18

def trusted(item,official_urls,state,cache,today,model,version):
    if not isinstance(item,dict):return False
    if item.get("review_status")!="auto_verified" or item.get("verification")!="two_independent_visual_passes":
        return False
    url=item.get("pdf_url","")
    if url not in official_urls:return False
    document_id=hashlib.sha256(url.encode()).hexdigest()[:16]
    record=state.get(document_id,{})
    sha=str(item.get("pdf_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",sha) or record.get("sha")!=sha:
        return False
    page=item.get("pdf_page")
    if type(page)!=int or page<1 or (page-1) not in record.get("done_pages",[]):
        return False
    try:when=dt.date.fromisoformat(str(item.get("date") or ""))
    except (TypeError,ValueError):return False
    if not today<=when<=today+dt.timedelta(days=120):return False
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",str(item.get("time") or "")):return False
    if not gate.safe_venue(item.get("venue")):return False
    if len(str(item.get("evidence") or ""))<18:return False
    first_key=f"{sha}/{page-1}/{model}/{version}/ai_vision"
    second_key=f"{sha}/{page-1}/{model}/{version}/independent_double_read"
    first=(cache.get(first_key) or {}).get("output") or {}
    second=(cache.get(second_key) or {}).get("output") or {}
    if not(first.get("page_is_program") and second.get("page_is_program")):return False
    first_records=first.get("events",[])
    second_records=second.get("events",[])
    if not isinstance(first_records,list) or not isinstance(second_records,list):return False
    return any(
        _record_matches(item,a) and _record_matches(item,b) and gate.same_record(a,b)
        and gate.confirmed_admission(a,b)==(
            item.get("admission_type") or "unknown",
            item.get("admission_details") or None)
        for a in first_records for b in second_records
    )

def cleanup_stale(conn, trusted_events):
    """Remove PDF-only listings unsupported by current verified evidence.

    Other municipal adapters and ticket feeds are deliberately untouched.
    """
    valid={(e["title"],e["start"],e["source_url"]) for e in trusted_events}
    rows=conn.execute("SELECT id,title,start,source_url FROM events WHERE source_name=?",
                      (gate.SOURCE,)).fetchall()
    deletions=[r[0] for r in rows if (r[1],r[2],r[3]) not in valid]
    if deletions:
        conn.executemany("DELETE FROM events WHERE id=?",[(i,) for i in deletions])
        conn.commit()
    return len(deletions)
