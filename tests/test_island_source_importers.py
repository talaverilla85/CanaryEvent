import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import fimc_island_agenda as fimc
import island_eventon_agendas as municipal
import island_source_intelligence as intelligence

TODAY=dt.date(2026,10,28)
FIMC_INDEX='''<div class="div-block-252">
 <h3 class="h3-nombre-artistas">MARIPOSAS NEGRAS EN CONCIERTO</h3>
 <div class="collection-item-30"><p fs-cmsfilter-field="ISLA">Tenerife</p>
 <p fs-cmssort-type="date">19/1/2027 19:30</p></div>
 <div class="collection-item-30"><p fs-cmsfilter-field="ISLA">Gran Canaria</p>
 <p fs-cmssort-type="date">22/1/2027 19:30</p></div>
 <a href="/espectaculos-fimc-2026/mariposas-negras">Entradas</a>
 </div>'''
FIMC_DETAIL='''<div class="collection-item-31"><div class="div-block-289"><div class="sin-20">Gran Canaria</div></div>
<div class="div-block-302"><div class="nunito-32">Teatro Guiniguada</div></div>
<div class="div-block-452">22 - 01 - 2027 | 19:30</div></div>
<div class="collection-item-31"><div class="div-block-289"><div class="sin-20">Tenerife</div></div>
<div class="div-block-302"><div class="nunito-32">Teatro Leal</div></div>
<div class="div-block-452">19 - 01 - 2027 | 19:30</div></div>'''

class IslandImporterTests(unittest.TestCase):
 def test_fimc_uses_two_independent_official_dates_and_island(self):
    index=BeautifulSoup(FIMC_INDEX,"html.parser")
    detail=BeautifulSoup(FIMC_DETAIL,"html.parser")
    upcoming=fimc.listing(index,TODAY)
    self.assertEqual(len(upcoming),1)
    self.assertEqual(upcoming[0]["date"],dt.date(2027,1,22))
    self.assertEqual(fimc.detail_matches(detail,upcoming[0]),["Teatro Guiniguada"])
    wrong={**upcoming[0],"time":"19:00"}
    self.assertEqual(fimc.detail_matches(detail,wrong),[])
    class Reader:
        def read(self,url):return index if url==fimc.INDEX else detail
    rows,report=fimc.collect(TODAY,reader=Reader())
    self.assertEqual(report["found"],1)
    self.assertEqual(len(rows),1)
    self.assertEqual(rows[0]["municipality"],"Las Palmas de Gran Canaria")
    self.assertEqual(rows[0]["start"],"2027-01-22T19:30:00")
    self.assertFalse(rows[0]["free"])
    self.assertEqual(rows[0]["price"],"")
 def test_fimc_rejects_external_links_and_wrong_halls(self):
    self.assertFalse(fimc.official_link("https://www.icdcultural.org.evil.org/espectaculos-fimc-2026/x"))
    self.assertFalse(fimc.official_link("http://www.icdcultural.org/espectaculos-fimc-2026/x"))
    p=fimc.listing(BeautifulSoup(FIMC_INDEX,"html.parser"),TODAY)[0]
    detail=BeautifulSoup(FIMC_DETAIL.replace("Teatro Guiniguada","Teatro del Otro Lugar"),"html.parser")
    self.assertEqual(fimc.detail_matches(detail,p),[])
 def test_municipal_eventon_credit_and_no_all_day_invention(self):
    source=municipal.SOURCES[0]
    item={
      "@type":"Event","name":"BLANCANIEVES, MÁS ALLÁ DEL ESPEJO",
      "url":"https://aguimes.es/events/blancanieves-mas-alla-del-espejo/",
      "startDate":"2026-11-7T18:30+0:00",
      "eventStatus":"https://schema.org/EventScheduled",
      "location":[{"@type":"Place","name":"Teatro Auditorio Agüimes"}],
      "description":"<p>Camino Viejo Producciones</p>"
    }
    bad={**item,"startDate":"2026-11-12"}
    bad_site={**item,"url":"https://attacker.example/events/blancanieves-mas-alla-del-espejo/"}
    html="".join('<div class="eventon_list_event"><script type="application/ld+json">'+json.dumps(e,ensure_ascii=False)+'</script></div>' for e in (item,bad,bad_site))
    rows,stats=municipal.parse(BeautifulSoup(html,"html.parser"),source,TODAY)
    self.assertEqual(len(rows),1)
    self.assertEqual(rows[0]["start"],"2026-11-07T18:30:00")
    self.assertEqual(rows[0]["municipality"],"Agüimes")
    self.assertIn("Camino Viejo Producciones",rows[0]["details"])
    self.assertEqual(stats["rejected"],2)
 def test_only_supported_island_publishes_and_tracks_producer(self):
    registry=json.loads((ROOT/"data/island_source_registry.json").read_text(encoding="utf8"))
    report=intelligence.build(registry,{"events":[{
        "title":"Blancanieves","start":"2026-11-07T18:30:00",
        "source_name":"Ayuntamiento de Agüimes · programación de teatros",
        "municipality":"Agüimes","venue":"Teatro Auditorio Agüimes",
        "source_url":"https://aguimes.es/events/blancanieves-mas-alla-del-espejo/",
        "details":"Camino Viejo Producciones · Producción acreditada en la web municipal."
    }]},{"sources":[]},TODAY)
    self.assertEqual(len(report["islands"]),8)
    self.assertEqual([s["island"] for s in report["islands"] if s["publication_enabled"]],["Gran Canaria"])
    self.assertEqual(report["source_count"],len(registry["source_profiles"]))
    self.assertEqual(len(report["producer_observations"]["Camino Viejo Producciones"]),1)
 def test_fimc_separate_island_is_not_gran_canaria(self):
    listing=fimc.listing(BeautifulSoup(FIMC_INDEX,"html.parser"),TODAY,island="Tenerife")
    self.assertEqual(len(listing),1)
    self.assertEqual(listing[0]["date"],dt.date(2027,1,19))
    # Other islands must not be published without their own venue mapping.
    self.assertFalse(fimc.detail_matches(BeautifulSoup(FIMC_DETAIL,"html.parser"),listing[0]))

if __name__=="__main__":unittest.main()
