"""Contract tests for future date filters and OR-based multiple categories."""
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
class DiscoveryFlexibleFilters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"public/index.html").read_text(encoding="utf8")
        cls.soup=BeautifulSoup(cls.html,"html.parser")
        cls.inline=cls.soup.find_all("script")[-1].get_text()
        cls.picker=(ROOT/"public/filter_ui.js").read_text(encoding="utf8")

    def test_mobile_date_selector_inputs(self):
        self.assertIsNotNone(self.soup.select_one("#customDateToggle"))
        self.assertEqual(self.soup.select_one("#filterMonth")["type"],"month")
        self.assertEqual(self.soup.select_one("#filterFrom")["type"],"date")
        self.assertEqual(self.soup.select_one("#filterTo")["type"],"date")
        self.assertIsNotNone(self.soup.select_one("#customDatePanel button[type=submit]"))
        self.assertIn("applyCustomDate()",self.inline)
        self.assertIn("dateRangeLabel",self.inline)

    def test_month_range_and_multiday_overlap(self):
        self.assertIn("Date.UTC(Number(month.slice(0,4)),Number(month.slice(5,7)),0)",self.picker)
        self.assertIn("start<=r.end&&end>=r.start",self.inline)
        self.assertIn("state.when='custom'",self.picker)
        self.assertIn("state.dateRange=range",self.picker)
        self.assertIn("state.when!=='custom'",self.inline)

    def test_categories_are_multiple_and_persisted_locally(self):
        self.assertIn("state.categories=new Set()",self.inline)
        self.assertIn("state.categories.has(e.category)",self.inline)
        self.assertIn("state.categories.add(k)",self.inline)
        self.assertIn("state.categories.delete(k)",self.inline)
        self.assertIn("state.categories.clear()",self.inline)
        self.assertIn("padonde_selected_categories",self.inline)
        self.assertNotIn("state.category=",self.inline)
        self.assertIn("aria-pressed",self.inline)

    def test_feature_assets_and_existing_features_preserved(self):
        self.assertTrue((ROOT/"public/sw.js").read_text(encoding="utf8").count("'/filter_ui.js'"))
        self.assertIn("reminderDetailBtn",self.inline)
        self.assertIn("sponsorCardHtml",self.inline)
        self.assertIn("requestCurrentLocation(false)",self.inline)
        self.assertIn("renderMapList",self.inline)

if __name__=="__main__":
    unittest.main()
