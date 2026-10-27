"""Conservative discovery radar across Gran Canaria municipal websites.

It finds official-site candidate links, not verified events. This is
read-only and explicitly never publishes an event or infers a date.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"data"/"municipal_sources_gc.json"
OUTPUT=ROOT/"data"/"gc_radar_leads.json"
UA="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
KEYWORDS=re.compile(r"fiest|eventos?\b|agenda|cultur|festival|concierto|finaos|halloween|feria|mercado|romer[ií]a|teatro|m[uú]sica|actuaci[oó]n",re.I)
GENERIC_LABELS={"leer más","leer mas","read more","más información","mas información","ver más"}
EXCLUDE=re.compile(r"^(?:#|mailto:|tel:|javascript:)",re.I)

def same_official_host(link, homepage):
    base=urlsplit(homepage)
    dest=urlsplit(link)
    if dest.scheme!="https" or not dest.hostname or dest.username or dest.password:
        return False
    host=base.hostname or ""
    target=dest.hostname or ""
    return (target==host or target.removeprefix("www.")==host.removeprefix("www.")) and not dest.query

def candidate_links(url,html,max_per_site=15):
    soup=BeautifulSoup(html,"html.parser")
    results={}
    for a in soup.select("a[href]"):
        label=" ".join(a.get_text(" ",strip=True).split())
        if label.casefold() in GENERIC_LABELS:
            parent=a.find_parent(["article","li"])
            header=parent.find(["h2","h3","h4"]) if parent else None
            label=" ".join(header.get_text(" ",strip=True).split()) if header else ""
        href=a.get("href","").strip()
        if not href or EXCLUDE.match(href):
            continue
        dest=urljoin(url,href)
        if not same_official_host(dest,url):
            continue
        if urlsplit(dest).path in ("/",""):
            continue
        path=urlsplit(dest).path.lower()
        if not KEYWORDS.search(label+" "+path):
            continue
        if len(label)<8 or re.search(
            r"ayuda escolar|subvenci[oó]n|tr[aá]mite|agenda institucional|escuela municipal|escuela de m[uú]sica",
            label,re.I):
            continue
        results[dest]={"url":dest,"label":label[:200],
                       "kind":"unverified_official_link"}
        if len(results)>=max_per_site:
            break
    return list(results.values())

def allowed(session,url):
    uri=urlsplit(url)
    if uri.scheme!="https" or not uri.hostname or uri.username or uri.password:
        raise ValueError("Only official HTTPS source URLs are accepted")
    robots=session.get(f"https://{uri.hostname}/robots.txt",timeout=12,
                       allow_redirects=False,headers={"User-Agent":UA})
    if robots.status_code in (404,410):
        return
    if robots.status_code!=200:
        raise RuntimeError("Robots unavailable")
    parsed=RobotFileParser()
    parsed.parse(robots.text.splitlines())
    if not parsed.can_fetch(UA,url):
        raise PermissionError("Robots explicitly denies source")

def inspect(session,source):
    url=source["official_website"]
    allowed(session,url)
    r=session.get(url,timeout=20,allow_redirects=False,
                  headers={"User-Agent":UA,"Accept":"text/html"})
    if r.status_code!=200:
        raise RuntimeError("Official homepage unavailable")
    if "html" not in r.headers.get("Content-Type","").lower() or len(r.content)>2_000_000:
        raise ValueError("Unrecognized or oversized official webpage")
    return candidate_links(url,r.content)

def run(argv=None,*,today=None,session=None,registry=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-sites",type=int,default=8)
    args=ap.parse_args(argv)
    if not 1<=args.max_sites<=12:
        ap.error("--max-sites must be between 1 and 12")
    today=today or dt.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    doc=registry or json.loads(REGISTRY.read_text(encoding="utf8"))
    previous=json.loads(OUTPUT.read_text(encoding="utf8")) if OUTPUT.exists() else {}
    status=previous.get("scan_state",{})
    all_leads={x["url"]:x for x in previous.get("leads",[]) if isinstance(x,dict) and x.get("url")}
    sources=[e for e in doc["municipalities"]
             if not e.get("status","").startswith("conector_activo")
             and e.get("official_website","").startswith("https://")]
    sources.sort(key=lambda e:(status.get(e["municipality"],{}).get("checked_on",""),e["municipality"]))
    inspected=[]
    sess=session or requests.Session()
    for source in sources[:args.max_sites]:
        municipio=source["municipality"]
        try:
            leads=inspect(sess,source)
            for lead in leads:
                record=all_leads.get(lead["url"],{})
                all_leads[lead["url"]]={
                    **lead,"municipality":municipio,
                    "first_seen":record.get("first_seen",today.isoformat()),
                    "last_seen":today.isoformat(),
                    "publication_status":"not_an_event",
                }
            item={"municipality":municipio,"outcome":"ok","links":len(leads)}
        except (requests.RequestException,RuntimeError,ValueError,PermissionError) as e:
            item={"municipality":municipio,"outcome":"needs_review",
                  "error_type":type(e).__name__,"links":0}
        status[municipio]={"checked_on":today.isoformat(),
                           "outcome":item["outcome"]}
        inspected.append(item)
    latest=sorted(all_leads.values(),key=lambda e:(e["last_seen"],e["municipality"],e["url"]),
                  reverse=True)[:300]
    result={"checked_on":today.isoformat(),"scope":"Gran Canaria (official candidate links only)",
            "no_auto_publication":True,
            "inspected":inspected,"scan_state":status,"candidate_count":len(latest),
            "leads":latest}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    temp.replace(OUTPUT)
    print(json.dumps({"sites":len(inspected),"candidates":len(latest),
                      "errors":sum(e["outcome"]!="ok" for e in inspected)},
                     ensure_ascii=False))
    return result

if __name__=="__main__":run()
