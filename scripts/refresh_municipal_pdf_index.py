"""Refresh official PDF programme inventory for Santa Lucia, Agüimes and Gáldar."""
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import municipal_pdf_sources as sources

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public"/"municipal_pdf_programs.json"
def update(*,today=None,session=None):
    today=today or dt.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    previous=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    result=sources.build_catalog(today.year,session,existing=previous)
    # Network failures must never silently remove approved inventory.
    if result["errors"]:
        kept={e["pdf_url"]:e for e in result["programs"]}
        for prior in previous.get("programs",[]):
            m=prior.get("municipality")
            url=prior.get("pdf_url")
            if (m in result["errors"] and url and
                sources.verified_pdf(url,m,int(prior.get("year",0))) and
                int(prior["year"])==today.year):
                kept.setdefault(url,prior)
        result["programs"]=sorted(kept.values(),key=lambda e:(e["municipality"],e["pdf_url"]))
        result["program_count"]=len(result["programs"])
    temp=OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    temp.replace(OUT)
    print(json.dumps({"programs":result["program_count"],"errors":result["errors"]},ensure_ascii=False))
    return result
if __name__=="__main__":update()
