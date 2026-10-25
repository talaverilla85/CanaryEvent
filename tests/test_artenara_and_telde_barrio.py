import unittest,sys,datetime as dt
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
import artenara_ferias as art
import telde_barrio_programs as barrios
import sync_events as sync

class ArtenaraOfficialAutumnTests(unittest.TestCase):
 def setUp(self):
  self.today=dt.date(2026,10,25)
  links="".join('<article><a href="'+x["url"]+'">'+x["title"]+'</a></article>' for x in art.ITEMS)
  archive='<main>Día: 9 de octubre de 2026 '+links+'</main>'
  pages={art.ARCHIVE:BeautifulSoup(archive,"html.parser"),art.CATEGORY:BeautifulSoup(links,"html.parser")}
  for item in art.ITEMS:
   article='<div class="elementor-widget-theme-post-content">'+", ".join(item["tokens"])+'</div>'
   pages[item["url"]]=BeautifulSoup(article,"html.parser")
  self.pages=pages
 def test_two_2026_fairs_with_no_unproven_prices_times(self):
  e=art.extract(self.pages,self.today,sync.PLACES,sync.category)
  self.assertEqual(len(e),2)
  self.assertEqual({x["start"] for x in e},{"2026-10-31","2026-11-01"})
  self.assertTrue(all(x["municipality"]=="Artenara" for x in e))
  self.assertTrue(all(x["free"] is None and x["price"]=="" for x in e))
  self.assertTrue(all(x["venue"].startswith("Consultar el recinto") for x in e))
 def test_no_annual_recurrence(self):
  self.assertEqual(art.extract(self.pages,dt.date(2026,11,2),sync.PLACES,sync.category),[])
 def test_missing_publication_proof_blocks(self):
  self.pages[art.ARCHIVE]=BeautifulSoup("<main>9 de octubre "+' '.join(x["url"] for x in art.ITEMS)+"</main>","html.parser")
  with self.assertRaises(ValueError):
   art.extract(self.pages,self.today,sync.PLACES,sync.category)
 def test_missing_article_claim_blocks(self):
  p=art.ITEMS[0]["url"]
  self.pages[p]=BeautifulSoup('<div class="elementor-widget-theme-post-content">mercadillo mensual</div>',"html.parser")
  with self.assertRaises(ValueError):
   art.extract(self.pages,self.today,sync.PLACES,sync.category)
class TeldeNeighbourhoodDiscoveryTests(unittest.TestCase):
 def test_official_pdf_links_only_never_create_events(self):
  html='''<article><div class="post-content">
  <a href="https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf">Fiestas del barrio de Caserones Altos</a>
  <a href="https://www.telde.es/wp-content/uploads/2025/10/old.pdf">Fiestas antiguas de 2025</a>
  <a href="https://stranger.example.com/wp-content/uploads/2026/10/evil.pdf">PDF externo fraudulento</a>
  <a href="https://www.telde.es/areas/ocio">Fiestas barrio de San Gregorio</a>
  </div></article>'''
  entries=barrios.extract(BeautifulSoup(html,"html.parser"),2026)
  self.assertEqual(len(entries),1)
  self.assertEqual(entries[0]["event_date_verified"],False)
  self.assertIn("Caserones",entries[0]["title"])
 def test_first_seen_preserved(self):
  item=dict(title="Barrio de la Cumbre",pdf_url="https://www.telde.es/wp-content/uploads/2026/11/a.pdf")
  out=barrios.merge_seen([item],[{**item,"first_seen_at":"2026-10-24T09:00:00Z"}],"2026-10-25T08:00:00Z")
  self.assertEqual(out[0]["first_seen_at"],"2026-10-24T09:00:00Z")
 def test_monitor_written_by_daily_workflow(self):
  p=(ROOT/"scripts/sync_events.py").read_text(encoding="utf8")
  self.assertIn("municipal_programs.json",p)
  self.assertIn("telde_barrio_programs.fetch_year",p)
  sh=(ROOT/"scripts/publish_synced_data.sh").read_text(encoding="utf8")
  self.assertIn("public/municipal_programs.json",sh)
if __name__=="__main__":unittest.main()
