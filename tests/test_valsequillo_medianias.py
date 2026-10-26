import datetime as dt
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import valsequillo_medianias as val
FACTS = " ".join(val.REQUIRED_PHRASES)

class ValsequilloSourceTests(unittest.TestCase):
    def _extract(self, text=FACTS, today=dt.date(2026, 10, 26)):
        soup = BeautifulSoup("<article><p>" + text + "</p></article>", "html.parser")
        return val.extract(soup, today, {"Valsequillo": None}, lambda _: "gastronomia")

    def test_two_distinct_verified_sessions(self):
        events = self._extract()
        self.assertEqual(len(events), 2)
        self.assertEqual([e["start"] for e in events], ["2026-10-31T10:00:00", "2026-11-01T10:00:00"])
        self.assertEqual([e["end"] for e in events], ["2026-10-31T19:00:00", "2026-11-01T16:00:00"])
        self.assertTrue(all(e["municipality"] == "Valsequillo" for e in events))
        self.assertTrue(all(e["free"] == 1 and e["price"] == "Gratis" for e in events))
        self.assertTrue(all(e["source_url"] == val.URL for e in events))

    def test_expiry(self):
        self.assertEqual(self._extract(today=dt.date(2026, 11, 2)), [])
        self.assertEqual(len(self._extract(today=dt.date(2026, 11, 1))), 1)

    def test_missing_price_or_hour_fails_closed(self):
        with self.assertRaises(ValueError):
            self._extract(FACTS.replace("entrada libre y gratuita", "consultar precio"))
        with self.assertRaises(ValueError):
            self._extract(FACTS.replace("10:00 a 16:00", "sin hora confirmada"))

    def test_missing_municipality_returns_no_event(self):
        soup = BeautifulSoup("<article>" + FACTS + "</article>", "html.parser")
        self.assertEqual(val.extract(soup, dt.date(2026,10,26), {"Teror":None}, lambda _:"gastronomia"), [])

    def test_robots_disallow(self):
        class Response:
            status_code = 200
            content = b""
            text = "User-agent: *\nDisallow: /noticias/\n"
        class Fake:
            calls = []
            def get(self, url, **kwargs):
                self.calls.append(url)
                return Response()
        fake = Fake()
        with self.assertRaises(PermissionError):val.fetch(fake)
        self.assertEqual(len(fake.calls), 1)

    def test_robots_unavailable_must_not_bypass(self):
        class Fake:
            def get(self, url, **kwargs):
                class Response: status_code = 403
                return Response()
        with self.assertRaises(RuntimeError):val.fetch(Fake())

if __name__=="__main__":unittest.main()
