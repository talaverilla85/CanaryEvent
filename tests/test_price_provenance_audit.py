from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_price_provenance as audit
def e(**kw):
 x={"id":1,"title":"Evento ficticio de prueba","price":"","free":None,"source_name":"Test","source_url":"https://example.org"}
 x.update(kw)
 return x
class PriceProvenanceTests(unittest.TestCase):
 def test_distinguish_free_fixed_minimum_and_zero(self):
  self.assertEqual(audit.parse_price(e(price="Gratis",free=1)),"free")
  self.assertEqual(audit.parse_price(e(price="5 €",free=0)),"fixed_positive")
  self.assertEqual(audit.parse_price(e(price="Desde 20 €",free=0)),"minimum_positive")
  self.assertEqual(audit.parse_price(e(price="Desde 0 €",free=0)),"minimum_zero_ambiguous")
  self.assertEqual(audit.parse_price(e(price="Gratis",free=0)),"inconsistent_free")
  self.assertEqual(audit.parse_price(e(price="10 €",free=1)),"contradictory_free")
 def test_include_all_known_costs_not_unpriced(self):
  report=audit.audit([e(id=1),e(id=2,price="Desde 0 €",free=0),e(id=3,free=1)])
  self.assertEqual(report["known_price_or_free"],2)
  self.assertEqual(len(report["issues"]),1)
  self.assertEqual(report["issues"][0]["id"],2)
 def test_live_ticket_comparison_detects_drift(self):
  row=e(id=1,price="Desde 15 €",free=0,
   source_url="https://www.tureservaonline.es/es/events/test-match")
  report=audit.audit([row],[{"slug":"test-match","lowest_fare":20,"is_free":False}])
  self.assertEqual(report["live_ticket_check"]["matched"],1)
  self.assertEqual(len(report["live_ticket_check"]["mismatched"]),1)
  self.assertEqual(report["live_ticket_check"]["mismatched"][0]["api_now"],"Desde 20 €")
if __name__=="__main__":unittest.main()
