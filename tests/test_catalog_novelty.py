"""Non-push discovery alerts: privacy-first new listings from previous catalogue."""
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
class NewEventBadgeContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=(ROOT/"public"/"index.html").read_text(encoding="utf8")
  cls.soup=BeautifulSoup(cls.html,"html.parser")
  cls.js=cls.soup.find_all("script")[-1].get_text()
 def test_only_counts_actual_new_event_ids(self):
  self.assertIn("padonde_known_event_ids_v1",self.js)
  self.assertIn("state.newEventIds=new Set([...valid].filter(id=>!old.has(id)))",self.js)
  self.assertIn("if(raw===null)",self.js)
  self.assertIn("state.newEventIds=new Set();state.newOnly=false;return",self.js)
 def test_ui_separates_in_app_notices_from_push(self):
  self.assertIsNotNone(self.soup.select_one("#newEventNotice"))
  self.assertIsNotNone(self.soup.select_one("#newEventSee"))
  self.assertIsNotNone(self.soup.select_one("#newEventDismiss"))
  self.assertIn("markNewEventsSeen",self.js)
  self.assertIn("scanNewEventIds(state.events)",self.js)
  self.assertIn("state.newOnly",self.js)
 def test_does_not_claim_push_without_backend(self):
  self.assertNotIn("Notification.requestPermission",self.js)
  self.assertNotIn("pushManager.subscribe",self.js)
  self.assertNotIn("navigator.geolocation",self.js[self.js.index("function scanNewEventIds("):self.js.index("function renderCategories(")])
 def test_sponsor_and_favorites_untouched(self):
  self.assertIn("sponsorCardHtml",self.js)
  self.assertIn("state.favorites.has",self.js)
  self.assertIn("openReminderDialog(e)",self.js)
if __name__=="__main__":unittest.main()
