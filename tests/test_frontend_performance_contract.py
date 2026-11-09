"""Guard the fast-first-render contract without changing user-facing features."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"public/index.html").read_text(encoding="utf-8-sig")
FILTERS=(ROOT/"public/filter_ui.js").read_text(encoding="utf-8")

class FrontendPerformanceContract(unittest.TestCase):
    def test_map_libraries_are_loaded_only_when_opened(self):
        head=HTML.split("</head>",1)[0]
        self.assertNotIn('rel="stylesheet" href="https://unpkg.com/leaflet',head)
        self.assertNotIn('<script src="https://unpkg.com/leaflet',HTML)
        self.assertIn("async function openMap()",HTML)
        self.assertIn("try{await loadLeaflet()}",HTML)
        self.assertIn("if(window.L)return Promise.resolve(window.L)",HTML)
        self.assertIn("if(leafletLoading)return leafletLoading",HTML)
        self.assertIn("thisOpen!==mapOpenSeq",HTML)
        self.assertIn("++mapOpenSeq;",HTML)
        self.assertIn("script.integrity='sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo='",HTML)
        self.assertIn("css.integrity='sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY='",HTML)
        self.assertIn("if(!state.map){",HTML)
        self.assertIn("state.map=L.map(",HTML)

    def test_initial_list_work_is_bounded_but_load_more_remains(self):
        self.assertIn("visibleLimit:24",HTML)
        self.assertNotIn("visibleLimit:48",HTML)
        self.assertNotIn("state.visibleLimit=48",HTML)
        self.assertIn("state.visibleLimit+=24;render()",HTML)
        self.assertIn("state.visibleLimit=24",FILTERS)
        self.assertIn("const shown=events.slice(0,state.visibleLimit)",HTML)

    def test_search_is_debounced_but_other_filters_are_immediate(self):
        self.assertIn("let searchRenderTimer=null",HTML)
        self.assertIn("setTimeout(()=>{searchRenderTimer=null;render()},140)",HTML)
        self.assertIn("clearTimeout(searchRenderTimer);searchRenderTimer=null;",HTML)
        self.assertIn("state.categories.clear();",HTML)
        self.assertIn("function chooseCategory(k)",HTML)
        self.assertIn("state.newOnly=false;render();",HTML)

    def test_catalog_filters_and_sort_are_bounded(self):
        self.assertIn("function inFilter(e,today=todayKey(),now=localTimeKey())",HTML)
        self.assertIn("function eventScore(e,now=localTimeKey())",HTML)
        self.assertIn("const now=localTimeKey(),today=now.slice(0,10)",HTML)
        self.assertIn("inFilter(e,today,now)",HTML)
        self.assertIn("unknownCache=new Map(),nearCache=new Map(),scoreCache=new Map()",HTML)
        self.assertIn("return score(a)-score(b)",HTML)

    def test_cards_survive_unrelated_render_without_reloading_posters(self):
        self.assertIn("let lastGridMarkup=null",HTML)
        self.assertIn("const nextGridMarkup=shown.map((e,i)=>",HTML)
        self.assertIn("if(nextGridMarkup!==lastGridMarkup)",HTML)
        self.assertIn("lastGridMarkup=nextGridMarkup",HTML)
        self.assertIn("loading=\"'+(large?'eager':'lazy')",HTML)
        self.assertIn("img.fetchPriority='high'",HTML)
        self.assertIn('fetchpriority="high"',HTML)
        self.assertIn("verifiedImage(e)",HTML)

    def test_catalog_cache_warms_page_safely_without_persisting_campaigns(self):
        self.assertIn("function showCachedCatalog()",HTML)
        self.assertIn("showCachedCatalog();\n loadEvents();",HTML)
        self.assertIn("function readCachedCatalog(maxAgeMs)",HTML)
        self.assertIn("EVENT_CACHE_WARM_MAX_AGE=24*60*60*1000",HTML)
        self.assertIn("EVENT_CACHE_OFFLINE_MAX_AGE=7*24*60*60*1000",HTML)
        self.assertIn("e.paid_promotion!==true",HTML)
        self.assertIn("requestIdleCallback(write,{timeout:1800})",HTML)
        self.assertIn("scheduleCatalogCache(state.events)",HTML)
        self.assertIn("path==='/api/events'?'default':'no-store'",HTML)
        self.assertIn("cache:'no-cache'",HTML)

    def test_no_features_or_prelaunch_controls_were_removed(self):
        self.assertIn('name="robots" content="noindex,nofollow"',HTML)
        for marker in ("<div id=\"app\"", "function openMap()", "function closeMap()",
                       "function showEvent(", "function toggleFav(", "function renderWeekendShelf()",
                       "function loadSponsored(", "const sponsorAt=sponsorInsertAfter()",
                       "function requestCurrentLocation(", "function loadEvents()",
                       "'/reminders.js'", "dparranda-editorial.css"):
            if marker=="'/reminders.js'":
                marker='/reminders.js'
            self.assertIn(marker,HTML)
        self.assertIn('href="/manifest.webmanifest?v=8"',HTML)

if __name__=="__main__":
    unittest.main()
