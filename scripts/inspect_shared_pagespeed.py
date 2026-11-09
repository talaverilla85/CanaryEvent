"""Diagnostic only: read shared PageSpeed report HTML (no site changes)."""
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import re

IDS=("3azvcb3414","08ye6lloa4","pcpgg8jta4")
class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("style","script"): self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("style","script"): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.items.append(data.strip())

for rid in IDS:
    url=f"https://pagespeed.web.dev/analysis/https-canaryevent-vercel-app/{rid}?form_factor=mobile"
    print("\n=== REPORT",rid,"===",flush=True)
    try:
        req=Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36", "Accept-Language":"es-ES,es;q=0.9"})
        with urlopen(req,timeout=18) as stream:
            raw=stream.read(6_000_000).decode("utf8","replace")
            print("HTTP",stream.status,"bytes",len(raw),flush=True)
        parser=Text()
        parser.feed(raw)
        visible=" | ".join(parser.items)
        print("VISIBLE_BODY",visible[:8000],flush=True)

        # Audit payload is an escaped Lighthouse JSON string. Two sets are
        # commonly embedded (desktop/mobile); print every occurrence so the
        # real mobile metrics can be identified by their numeric values.
        for name in ("performance","first-contentful-paint","largest-contentful-paint",
                     "total-blocking-time","speed-index","cumulative-layout-shift"):
            marker='\\\\"'+name+'\\\\":{'
            candidates=[]
            cursor=0
            while True:
                ix=raw.find(marker,cursor)
                if ix<0: break
                piece=raw[ix:ix+1400]
                score=re.search(r'\\\\\"score\\\\\":([0-9.]+|null)',piece)
                numeric=re.search(r'\\\\\"numericValue\\\\\":([0-9.]+)',piece)
                candidates.append({"score":score.group(1) if score else None,
                                   "numeric":numeric.group(1) if numeric else None})
                cursor=ix+len(marker)
            print("METRIC",name,candidates[:10],flush=True)
        for kw in ("First Contentful Paint","Total Blocking Time","Speed Index","Largest Contentful Paint","Rendimiento","performanceScore","lighthouseResult","categories"):
            pos=raw.lower().find(kw.lower())
            print("MATCH",kw,pos,repr(raw[max(0,pos-170):pos+500])[:700] if pos>=0 else "-",flush=True)
    except Exception as exc:
        print("FETCH_ERROR",type(exc).__name__,str(exc)[:300],flush=True)
