"""Contract tests for location-first discovery and readable event cards."""
import re
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]

class GeoCardContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"public"/"index.html").read_text(encoding="utf8")
        cls.soup=BeautifulSoup(cls.html,"html.parser")
        cls.js=cls.soup.find_all("script")[-1].get_text()
    def test_auto_geolocation_and_browser_permission(self):
        self.assertIn("requestCurrentLocation(false);",self.js)
        self.assertIn("navigator.geolocation.getCurrentPosition(",self.js)
        self.assertIn("navigator.permissions.query({name:'geolocation'})",self.js)
        self.assertIn("window.isSecureContext",self.js)
        self.assertIn("timeout:12000,maximumAge:0",self.js)
    def test_location_not_persisted_and_manual_choice_safe(self):
        self.assertIn("state.origin=[coords.latitude,coords.longitude]",self.js)
        self.assertNotIn("localStorage.setItem('plangc_coords'",self.js)
        self.assertNotIn("localStorage.setItem('plangc_location'",self.js)
        self.assertIn("state.geoRequestSeq++;state.origin=n?",self.js)
        self.assertIn("state.geoManualOverride=true",self.js)
        self.assertIn("if(seq!==state.geoRequestSeq)return",self.js)
        self.assertIn("if(document.hidden||state.geoManualOverride",self.js)
    def test_card_date_and_distance_in_content(self):
        self.assertIn('event-date-chip',self.html)
        self.assertIn("function cardDateLabel(e){",self.js)
        self.assertIn("'En curso · hasta '",self.js)
        self.assertIn("line-clamp:3",self.html)
        self.assertIn("≈ '+approx+' km",self.js)
        self.assertIn("Distancia aproximada en línea recta al centro del municipio",self.html)
        self.assertIn("Ver zona ↗",self.js)
        self.assertIn(".event-card{border-color:#dce6df;box-shadow:",self.html)
    def test_stable_other_features(self):
        self.assertIn("sponsorCardHtml",self.js)
        self.assertIn("sponsorAfter",self.html) if "sponsorAfter" in self.html else self.assertIn("sponsorInsertAfter",self.js)
        self.assertIn("function renderMapList()",self.js)
        self.assertIn("function loadEvents()",self.js)
        self.assertIn("state.favorites",self.js)

if __name__=="__main__":unittest.main()
