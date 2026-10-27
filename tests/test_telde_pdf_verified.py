"""Two-pass PDF visual consistency and publication proof."""
import datetime as dt
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_verified as v

FIRST={"title":"Concierto de música popular","date":"2026-11-07","time":"20:30",
       "venue":"Plaza de Caserones Altos","evidence":"Sábado 7 noviembre 20:30 concierto música popular Caserones Altos",
       "type":"musica"}
SECOND={**FIRST,"evidence":"Concierto de música popular el 7 noviembre 20:30"}
class DoubleVisualVerification(unittest.TestCase):
 def test_exact_independent_agreement_allows_only_upcoming(self):
  approved=v.approved_candidates([FIRST],[SECOND],today=dt.date(2026,10,27))
  self.assertEqual(len(approved),1)
  e=v.approved_to_event({**FIRST,"pdf_page":7,"pdf_sha256":"a"*64,
                         "pdf_url":"https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf"})
  self.assertEqual(e["municipality"],"Telde")
  self.assertEqual(e["start"],"2026-11-07T20:30:00")
  self.assertIsNone(e["free"])
  self.assertEqual(e["price"],"")
  self.assertEqual(e["verification"],"two_independent_visual_passes")
 def test_conflicting_hour_blocks_publication(self):
  self.assertEqual(v.approved_candidates([FIRST],[{**SECOND,"time":"21:30"}],today=dt.date(2026,10,27)),[])
 def test_conflicting_venue_blocks_publication(self):
  self.assertEqual(v.approved_candidates([FIRST],[{**SECOND,"venue":"Iglesia de Caserones Altos"}],today=dt.date(2026,10,27)),[])
 def test_conflicting_date_blocks_publication(self):
  self.assertEqual(v.approved_candidates([FIRST],[{**SECOND,"date":"2026-11-08"}],today=dt.date(2026,10,27)),[])
 def test_unknown_venue_blocks_publication(self):
  self.assertEqual(v.approved_candidates([{**FIRST,"venue":None}],[SECOND],today=dt.date(2026,10,27)),[])
  self.assertEqual(v.approved_candidates([FIRST],[{**SECOND,"venue":"Por confirmar"}],today=dt.date(2026,10,27)),[])
 def test_generic_program_title_blocks_publication(self):
  first={**FIRST,"title":"Programa de fiestas 2026"}
  second={**SECOND,"title":"Programa de fiestas 2026"}
  self.assertEqual(v.approved_candidates([first],[second],today=dt.date(2026,10,27)),[])
 def test_expired_or_too_far_out_blocks_publication(self):
  self.assertEqual(v.approved_candidates([FIRST],[SECOND],today=dt.date(2026,11,8)),[])
  self.assertEqual(v.approved_candidates([FIRST],[SECOND],today=dt.date(2026,2,1)),[])
 def test_no_evidence_blocks_publication(self):
  self.assertEqual(v.approved_candidates([FIRST],[{**SECOND,"evidence":"visto"}],today=dt.date(2026,10,27)),[])
 def test_text_still_in_review_if_no_second_pass(self):
  self.assertEqual(v.approved_candidates([FIRST],[],today=dt.date(2026,10,27)),[])
if __name__=="__main__":unittest.main()
