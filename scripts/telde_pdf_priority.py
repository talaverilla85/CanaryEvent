"""Conservative prioritization for municipal PDF ingestion.

An upload timestamp or a single past event does not prove a programme ended.
Past-only, partly read PDFs are *deferred*, not declared completed; new/unread
programmes and programmes with future dated activities get first consideration.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import re
from urllib.parse import urlsplit

PAUSE_DAYS = 7
PAST_ONLY_GRACE_DAYS = 7
MAX_FUTURE_DAYS = 120


def doc_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def day_of(value):
    try:
        return dt.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def upload_age_months(url: str, today: dt.date):
    match = re.match(r"/wp-content/uploads/(20\d{2})/(\d{2})/",
                     urlsplit(url).path)
    if not match:
        return None
    year, month = map(int, match.groups())
    if not 1 <= month <= 12:
        return None
    return (today.year - year) * 12 + today.month - month


def dated_records(url: str, records, checkpoint=None):
    sha = (checkpoint or {}).get("sha")
    return [day for e in records
            if isinstance(e, dict) and e.get("pdf_url") == url
            if not sha or e.get("pdf_sha256") == sha
            if (day := day_of(e.get("date"))) is not None]


def future_dated(url: str, records, today: dt.date, checkpoint=None):
    return any(today <= day <= today + dt.timedelta(days=MAX_FUTURE_DAYS)
               for day in dated_records(url, records, checkpoint))


def old_only_partial(url: str, checkpoint: dict, records, today: dt.date):
    """Suggest a short pause, without claiming unsampled pages are expired."""
    if checkpoint.get("complete") or len(checkpoint.get("done_pages", [])) < 2:
        return False
    dates = dated_records(url, records, checkpoint)
    return bool(dates) and max(dates) < today - dt.timedelta(days=PAST_ONLY_GRACE_DAYS)


def end_date_confirmed(program: dict, checkpoint: dict, today: dt.date):
    """Optional explicitly verified official-document end date.

    The date must be independently supplied and bound to the exact PDF SHA;
    dates inferred from file upload paths or event titles are NEVER enough.
    """
    end = day_of(program.get("verified_program_end"))
    declared_sha = program.get("verified_program_end_pdf_sha256")
    return bool(end and end < today and checkpoint.get("sha") and
                declared_sha == checkpoint["sha"] and
                re.fullmatch(r"[0-9a-f]{64}", str(declared_sha)) and
                program.get("verified_program_end_source") == program.get("pdf_url"))


def sorted_programs(index: dict, today: dt.date, state: dict, records):
    result = []
    for item in index.get("programs", []):
        if not isinstance(item, dict) or not item.get("pdf_url"):
            continue
        url = item["pdf_url"]
        age = upload_age_months(url, today)
        checkpoint = state.get(doc_id(url), {})
        if age is None or not (-1 <= age <= 2 or future_dated(url, records, today, checkpoint)):
            continue
        # A source with independently dated future acts remains eligible even
        # when uploaded a few months before its event.
        future = future_dated(url, records, today, checkpoint)
        is_complete = bool(checkpoint.get("complete"))
        has_scanned = bool(checkpoint.get("done_pages", []))
        past_only = old_only_partial(url, checkpoint, records, today)
        # Future activities first, then new unknown PDFs, then incomplete PDFs.
        # Stale, past-only documents go behind other candidates.
        bucket = (0 if future and not is_complete else
                  1 if not has_scanned and not is_complete else
                  3 if past_only else
                  2 if not is_complete else 4)
        result.append((bucket, age if age is not None else 99, url, item))
    # Newer upload month wins within the same priority; no date is inferred
    # from the PDF filename or upload month.
    return [item for _, __, ___, item in sorted(
        result, key=lambda row: (row[0], row[1], row[2]))]


def pause_active(checkpoint: dict, today: dt.date):
    until = day_of(checkpoint.get("defer_until"))
    return bool(until and today < until)


def defer(checkpoint: dict, today: dt.date):
    checkpoint["defer_until"] = (today + dt.timedelta(days=PAUSE_DAYS)).isoformat()
    checkpoint["defer_reason"] = "only_old_acts_seen_so_far_unread_pages_remain"
    return checkpoint
