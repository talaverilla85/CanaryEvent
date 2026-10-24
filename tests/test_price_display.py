import unittest
from pathlib import Path

HTML=(Path(__file__).resolve().parents[1]/"public"/"index.html").read_text(encoding="utf-8")

class PriceDisplayTests(unittest.TestCase):
 def test_unknown_price_not_displayed(self):
  self.assertNotIn("Precio por confirmar",HTML)
  self.assertNotIn("No hemos encontrado un importe oficial confirmado",HTML)
  self.assertIn("const price=e=>e.free===1?'Gratis':(e.price||'').trim();",HTML)
 def test_card_price_only_when_verified(self):
  self.assertIn("price(e)?",HTML)
  self.assertIn("event-bottom .distance{margin-left:auto}",HTML)
 def test_modal_price_row_conditional(self):
  self.assertIn("Comprueba las condiciones de acceso con la organización.",HTML)
  self.assertIn('class="event-dateblock"><span class="ico">€</span>',HTML)

if __name__=="__main__":unittest.main()
