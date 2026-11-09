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
