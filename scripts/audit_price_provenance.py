"""Audit *all* known-price public CanaryEvent entries without inventing prices.

The report distinguishes locally consistent labels from tariffs independently
revalidated against the platform's current read-only official API. It flags
"Desde 0 €" as ambiguous, never automatically upgrades it to 'Gratis'.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, json, re, sys
from pathlib import Path
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import ticket_reserva

MINIMUM=re.compile(r"^Desde (\d+(?:,\d{1,2})?) €$")
FIXED=re.compile(r"^(\d+(?:,\d{1,2})?) €$")
def parse_price(event):
    label=str(event.get("price") or "").strip()
    free=event.get("free")
    if free==1 and label in ("Gratis",""):return "free"
    if label=="Gratis" and free!=1:return "inconsistent_free"
    if free==1 and label not in ("Gratis",""):return "contradictory_free"
    m=MINIMUM.fullmatch(label)
    if m:
        val=Decimal(m.group(1).replace(",","."))
        return "minimum_zero_ambiguous" if val==0 else "minimum_positive"
    m=FIXED.fullmatch(label)
    if m:
        val=Decimal(m.group(1).replace(",","."))
        return "fixed_zero_ambiguous" if val==0 else "fixed_positive"
    if not label:return "missing"
    return "unrecognized"
def audit(events,live_listings=None):
    priced=[e for e in events if str(e.get("price") or "").strip() or e.get("free")==1]
    classifications=collections.Counter(parse_price(e) for e in priced)
    issue_status={"minimum_zero_ambiguous","fixed_zero_ambiguous","inconsistent_free","contradictory_free","unrecognized"}
    issues=[]
    for event in priced:
        status=parse_price(event)
        if status in issue_status:
            issues.append(dict(id=event.get("id"),title=event.get("title"),source=event.get("source_name"),label=event.get("price"),free=event.get("free"),category=status,url=event.get("source_url")))
    by_source=collections.Counter(e.get("source_name") for e in priced)
    live_results={"status":"not_checked","matched":0,"price_matched":0,"mismatched":[],"missing_from_current_listing":0,"not_direct_ticket_url":0}
    if live_listings is not None:
        by_slug={str(e.get("slug") or ""):e for e in live_listings if isinstance(e,dict) and e.get("slug")}
        live_results.update(status="checked",api_items=len(by_slug))
        for e in priced:
            url=str(e.get("source_url") or "")
            parts=urlsplit(url)
            if parts.hostname!="www.tureservaonline.es" or "/es/events/" not in parts.path:continue
            slug=parts.path.rstrip("/").split("/")[-1]
            item=by_slug.get(slug)
            if item is None:
                live_results["missing_from_current_listing"]+=1
                continue
            live_results["matched"]+=1
            raw=item.get("lowest_fare")
            try:
                val=Decimal(str(raw))
                expected=f"Desde {str(int(val)) if val==int(val) else str(val).replace('.',',')} €"
                if item.get("is_free") is True:expected="Gratis"
                actual=str(e.get("price") or "")
                if actual==expected:live_results["price_matched"]+=1
                else:live_results["mismatched"].append(dict(id=e.get("id"),title=e.get("title"),was=actual,api_now=expected,url=url))
            except (InvalidOperation,ValueError,TypeError):
                live_results["mismatched"].append(dict(id=e.get("id"),title=e.get("title"),was=e.get("price"),api_now=None,url=url))
    return {"checked_on":dt.datetime.now(dt.timezone.utc).isoformat(),"total_events":len(events),"known_price_or_free":len(priced),
        "classification":dict(classifications),"known_by_source":dict(by_source),"issues":issues,"live_ticket_check":live_results,
        "notes":["Label classification is not independent verification of each publisher's price.",
                 "Multiple event entries may share a ticket tariff; the live API check is only for matching direct ticket links.",
                 "Some events legitimately have free and paid ticket categories: Desde 0 € does not imply a completely free event."]}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--live-tickets",action="store_true")
    ap.add_argument("--output",default="")
    args=ap.parse_args()
    data=json.loads((ROOT/"public/events.json").read_text(encoding="utf8"))
    events=data["events"]
    live=None
    if args.live_tickets:
        try:live=ticket_reserva.fetch_listings()
        except Exception as ex:print("LIVE_TICKETS_ERROR",type(ex).__name__,str(ex)[:180],file=sys.stderr)
    result=audit(events,live)
    if args.live_tickets and live is None:result["live_ticket_check"]["status"]="source_unavailable"
    serialized=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(serialized+"\n",encoding="utf8")
    print("TOTAL",result["total_events"],"KNOWN",result["known_price_or_free"],"CLASSIFICATION",result["classification"])
    print("ISSUES",len(result["issues"]))
    for issue in result["issues"]:print("ISSUE",issue["id"],issue["category"],issue["label"],issue["title"][:85])
    print("LIVE_TICKETS",result["live_ticket_check"])
if __name__=="__main__":main()
