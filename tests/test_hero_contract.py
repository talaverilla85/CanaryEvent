"""Hero layout regression checks. Visual responsiveness is also checked via Playwright."""
from pathlib import Path
import unittest

HTML=(Path(__file__).resolve().parents[1]/"public"/"index.html").read_text(encoding="utf-8")

class HeroContractTests(unittest.TestCase):
    def test_decorations_cannot_cover_content(self):
        self.assertIn(".hero-grain,.hero-orbit,.hero-star",HTML)
        self.assertIn("z-index:0;pointer-events:none;user-select:none",HTML)
        self.assertIn("position:relative;z-index:3;",HTML)
        self.assertIn(".hero-star{opacity:.25}",HTML)
    def test_mobile_hero_has_no_vertical_tag(self):
        self.assertIn("@media (max-width:649px)",HTML)
        self.assertIn(".hero-tag{display:none}",HTML)
        self.assertIn("top:auto;bottom:18px;right:9px",HTML)
    def test_hero_accessible_decorations(self):
        # New editorial cover preserves named navigation and discoverability.
        self.assertIn('class="dp-masthead shell" aria-label="Portada de DParranda"',HTML)
        self.assertIn('class="dp-mark" aria-label="DParranda, volver al inicio"',HTML)
        self.assertIn('alt="DParranda"',HTML)
        self.assertIn('class="dp-stage"',HTML)
        self.assertIn('id="dpHeroToday"',HTML)
        self.assertIn('id="dpHeroWeekend"',HTML)
        self.assertIn('id="dpFeaturedOpen" aria-label="Ver evento destacado"',HTML)
        self.assertIn('id="dpPulseSurprise"',HTML)
        self.assertIn('id="surpriseBtn"',HTML)

if __name__=="__main__":unittest.main()
