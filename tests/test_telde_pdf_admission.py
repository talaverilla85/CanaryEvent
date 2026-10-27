import datetime as dt
import hashlib
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_auto as auto
import telde_pdf_vision as vision
import telde_pdf_verified as verified
import telde_pdf_integrity as integrity

URL="https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf"
SHA="e4816f361dcaf1ec43ff7b1bc42a47b4c017fa8d2845828c417e9803392e48b0"
DAY=dt.date(2026,10,27)
BASE={"title":"Concierto local de otoño","date":"2026-11-07","time":"20:30",
      "venue":"Plaza de Caserones Altos", "type":"musica",
      "evidence":"7 de noviembre, 20:30 Concierto local de otoño, Plaza de Caserones Altos"}
UID=hashlib.sha256(URL.encode()).hexdigest()[:16]

def validate(record):
    entry,error=vision.validate_candidate(record,2026,"Programa",
        URL,SHA,0,DAY)
    if error:raise AssertionError(error)
    return entry

def cache_for(first,second):
    pre=f"{SHA}/0/{vision.MODEL}/{auto.VERSION}"
    return {
        pre+"/ai_vision":{"output":{"events":[first],"page_is_program":True}},
        pre+"/independent_double_read":{"output":{"events":[second],"page_is_program":True}},
    }

class AdmissionEvidenceTests(unittest.TestCase):
    def test_schema_forces_explicit_admission_or_unknown(self):
        schema=vision.SCHEMA["properties"]["events"]["items"]
        self.assertIn("admission_type",schema["required"])
        self.assertIn("admission_details",schema["required"])
        self.assertEqual(set(schema["properties"]["admission_type"]["enum"]),
                         {"free","paid","donation","unknown"})

    def test_unknown_does_not_mean_free(self):
        row=validate(BASE)
        self.assertEqual(row["admission_type"],"unknown")
        self.assertIsNone(row["admission_details"])

    def test_literal_donation_retained_and_not_free(self):
        first={**BASE,"admission_type":"donation","admission_details":"Donativo 3 €"}
        second={**first,"evidence":"Concierto local de otoño 7 noviembre 20:30 Plaza de Caserones Altos"}
        approved=verified.approved_candidates([first],[second],today=DAY)
        self.assertEqual(len(approved),1)
        self.assertEqual(approved[0]["admission_type"],"donation")
        entry=verified.approved_to_event({**validate(approved[0]),**approved[0],"pdf_page":1,"pdf_sha256":SHA,"pdf_url":URL})
        self.assertIsNone(entry["free"])
        self.assertEqual(entry["price"],"Donativo 3 €")

    def test_disagreeing_price_downgrades_to_unknown(self):
        first={**BASE,"admission_type":"paid","admission_details":"Entrada 8 €"}
        second={**first,"admission_details":"Entrada 10 €"}
        approved=verified.approved_candidates([first],[second],today=DAY)
        self.assertEqual(approved[0]["admission_type"],"unknown")
        self.assertIsNone(approved[0]["admission_details"])
        entry=verified.approved_to_event({**approved[0],"pdf_page":1,"pdf_url":URL,"pdf_sha256":SHA})
        self.assertEqual(entry["price"],"")
        self.assertIsNone(entry["free"])

    def test_explicit_free_requires_double_confirmation(self):
        first={**BASE,"admission_type":"free","admission_details":None}
        agree=verified.approved_candidates([first],[first],today=DAY)[0]
        self.assertEqual(verified.approved_to_event({**agree,"pdf_page":1,"pdf_url":URL,"pdf_sha256":SHA})["price"],"Gratis")
        self.assertEqual(verified.approved_to_event({**agree,"pdf_page":1,"pdf_url":URL,"pdf_sha256":SHA})["free"],1)
        differ=verified.approved_candidates([first],[{**first,"admission_type":"unknown"}],today=DAY)[0]
        self.assertIsNone(verified.approved_to_event({**differ,"pdf_page":1,"pdf_url":URL,"pdf_sha256":SHA})["free"])

    def test_unsubstantiated_donation_is_downgraded(self):
        row=validate({**BASE,"admission_type":"donation","admission_details":"3 €"})
        self.assertEqual(row["admission_type"],"unknown")
        row=validate({**BASE,"admission_type":"paid","admission_details":"supuestamente"})
        self.assertEqual(row["admission_type"],"unknown")

    def test_price_integrity_requires_both_pdf_passes(self):
        one={**BASE,"admission_type":"donation","admission_details":"Donativo 3 €"}
        two={**one,"evidence":"Concierto local de otoño 7 noviembre 20:30 Plaza"}
        approved=verified.approved_candidates([one],[two],today=DAY)[0]
        record={**validate(approved),"review_status":"auto_verified",
                "verification":"two_independent_visual_passes"}
        state={UID:{"sha":SHA,"done_pages":[0]}}
        self.assertTrue(integrity.trusted(record,{URL},state,cache_for(one,two),
                                          DAY,vision.MODEL,auto.VERSION))
        tampered={**record,"admission_details":"Donativo 30 €"}
        self.assertFalse(integrity.trusted(tampered,{URL},state,cache_for(one,two),
                                           DAY,vision.MODEL,auto.VERSION))

    def test_midnight_needs_manual_date_review(self):
        at_midnight={**BASE,"time":"00:00"}
        self.assertEqual(verified.approved_candidates([at_midnight],[at_midnight],today=DAY),[])

if __name__=="__main__":
    unittest.main()
