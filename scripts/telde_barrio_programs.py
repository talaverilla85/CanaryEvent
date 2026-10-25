"""Read-only discovery of municipal PDF festival programs in Telde.

This adapter indexes only links and titles in the official municipal 2026
page. It intentionally DOES NOT create events from PDF filenames or calendar
months: the actual programs still need audited, dated extraction.
"""
import datetime as dt
import re,requests,html
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from pathlib import PurePosixPath

NAME="Ayuntamiento de Telde · índice de programas PDF"
BASE="https://www.telde.es"
UA="CanaryEventBot/0.1 (+https://github.com/talaverilla85/CanaryEvent)"
HEADERS={"User-Agent":UA}

def index_url(year):
    return f"{BASE}/areas/ocio-cultura-y-juventud/festejos-y-ferias/relacion-de-fiestas-ano-{year}/"

def fetch_year(year,client=requests):
    url=index_url(year)
    robots=client.get(BASE+"/robots.txt",headers=HEADERS,timeout=12,allow_redirects=False)
    if robots.status_code!=200:raise RuntimeError(f"Telde festival-index robots HTTP {robots.status_code}")
    p=RobotFileParser();p.parse(robots.text.splitlines())
    if not p.can_fetch(UA,url):raise PermissionError("Telde disallows festival-program index")
    response=client.get(url,headers=HEADERS,timeout=22,allow_redirects=False)
    if response.status_code!=200:raise RuntimeError(f"Telde festival index HTTP {response.status_code}")
    if len(response.content)>2_000_000:raise ValueError("Telde festival index unexpectedly large")
    return BeautifulSoup(response.content,"html.parser")

def extract(soup,year):
    area=soup.select_one("article .post-content") or soup.select_one("article")
    if area is None:raise ValueError("Telde festival index missing article")
    all_links={}
    for a in area.select("a[href]"):
        u=a["href"].strip()
        url=urlsplit(u)
        path=url.path.lower()
        if not(url.scheme=="https" and url.hostname=="www.telde.es" and
                path.startswith(f"/wp-content/uploads/{year}/") and
                path.endswith(".pdf")):
            continue
        title=" ".join(html.unescape(a.get_text(" ",strip=True)).split())[:220]
        if len(title)<10:continue
        all_links[u]={"title":title,"pdf_url":u,"year":year,"event_date_verified":False,
                      "note":"Programa detectado: fechas y actividades interiores pendientes de lectura validada"}
    if year==2026 and not all_links:raise ValueError("Telde 2026 index no longer lists municipal PDF programs")
    return sorted(all_links.values(),key=lambda x:x["pdf_url"])

def merge_seen(records,old,checked):
    previous={r["pdf_url"]:r for r in old if isinstance(r,dict) and r.get("pdf_url")}
    merged=[]
    for record in records:
        it=dict(record)
        it["first_seen_at"]=previous.get(it["pdf_url"],{}).get("first_seen_at",checked)
        merged.append(it)
    return merged
