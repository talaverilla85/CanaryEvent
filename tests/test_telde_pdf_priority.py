"""Future-first PDF scheduling, expiration archive and zero-cost expiry maintenance."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import telde_pdf_auto as auto
import telde_pdf_priority as p
import telde_pdf_vision as vision

TODAY=dt.date(2026,10,27)
CASERONES="https://www.telde.es/wp-content/uploads/2026/10/caseronesaltos26.pdf"
VALLE="https://www.telde.es/wp-content/uploads/2026/09/vallelosnuevealto26.pdf"
OLD="https://www.telde.es/wp-content/uploads/2026/06/old.pdf"
SHA="f"*64

def doc(url):
    return {"pdf_url":url,"title":"Fiestas locales","year":2026}
def row(url,date,title="Actuación",id="event-one"):
    return {"id":id,"title":title,"date":date,"time":"19:00",
            "venue":"Plaza municipal de Telde","pdf_url":url,
            "pdf_sha256":SHA,"pdf_page":2,"review_status":"pending_review"}

class PdfPriorityTests(unittest.TestCase):
    def test_future_event_takes_precedence_even_in_older_pdf(self):
        index={"programs":[doc(CASERONES),doc(VALLE),doc(OLD)]}
        rows=[row(OLD,"2026-11-20")]
        res=p.sorted_programs(index,TODAY,{},rows)
        self.assertEqual(res[0]["pdf_url"],OLD)
        self.assertEqual(len(res),3)

    def test_new_files_rank_ahead_of_past_only_scanned(self):
        index={"programs":[doc(CASERONES),doc(VALLE)]}
        state={p.doc_id(CASERONES):{"sha":SHA,"done_pages":[0,1,2],"complete":False}}
        archived=[row(CASERONES,"2026-10-10")]
        res=p.sorted_programs(index,TODAY,state,archived)
        self.assertEqual(res[0]["pdf_url"],VALLE)
        self.assertEqual(res[1]["pdf_url"],CASERONES)

    def test_unseen_pages_are_not_dubbed_completed(self):
        checkpoint={"sha":SHA,"done_pages":[0,1],"complete":False}
        self.assertTrue(p.old_only_partial(CASERONES,checkpoint,[row(CASERONES,"2026-10-10")],TODAY))
        self.assertFalse(p.old_only_partial(CASERONES,checkpoint,[row(CASERONES,"2026-11-10")],TODAY))
        self.assertFalse(p.old_only_partial(CASERONES,{"done_pages":[0]},[row(CASERONES,"2026-10-10")],TODAY))
        p.defer(checkpoint,TODAY)
        self.assertTrue(p.pause_active(checkpoint,TODAY+dt.timedelta(days=6)))
        self.assertFalse(p.pause_active(checkpoint,TODAY+dt.timedelta(days=7)))

    def test_explicit_end_requires_exact_sha_evidence_not_filename(self):
        checkpoint={"sha":SHA}
        fake={**doc(CASERONES),
              "verified_program_end":"2026-10-25",
              "verified_program_end_pdf_sha256":SHA,
              "verified_program_end_source":CASERONES}
        self.assertTrue(p.end_date_confirmed(fake,checkpoint,TODAY))
        self.assertFalse(p.end_date_confirmed({**fake,"verified_program_end_pdf_sha256":"b"*64},checkpoint,TODAY))
        self.assertFalse(p.end_date_confirmed({**fake,"verified_program_end_source":"guess"},checkpoint,TODAY))
        self.assertFalse(p.end_date_confirmed(doc(CASERONES),checkpoint,TODAY))

    def test_archive_idempotent_and_preserves_provenance(self):
        pending={"one":row(CASERONES,"2026-10-10",id="one"),
                 "two":row(CASERONES,"2026-11-10",id="two")}
        verified={"three":{**row(VALLE,"2026-10-11",id="three"),"review_status":"auto_verified"}}
        archive={}
        self.assertEqual(auto.archive_expired(TODAY,pending,verified,archive),2)
        self.assertEqual(list(pending),["two"])
        self.assertEqual(verified,{})
        self.assertEqual(len(archive),2)
        self.assertEqual(auto.archive_expired(TODAY,pending,verified,archive),0)
        self.assertEqual(len(archive),2)
        first=list(archive.values())[0]
        self.assertEqual(first["pdf_page"],2)
        self.assertEqual(first["pdf_sha256"],SHA)
        self.assertEqual(first["review_status"],"archived")

    def test_archive_only_has_no_external_requests_or_spend(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp)
            (t/"index.json").write_text(json.dumps({"programs":[doc(CASERONES)]}),encoding="utf8")
            (t/"pending.json").write_text(json.dumps([row(CASERONES,"2026-10-10"),
                                                     row(CASERONES,"2026-11-03",id="later")]),encoding="utf8")
            (t/"verified.json").write_text("[]",encoding="utf8")
            with patch.object(auto,"REVIEW",t/"pending.json"), \
                 patch.object(auto,"VERIFIED",t/"verified.json"), \
                 patch.object(auto,"CACHE",t/"cache.json"), \
                 patch.object(auto,"STATE",t/"state.json"), \
                 patch.object(auto,"REPORT",t/"report.json"), \
                 patch.object(vision,"SOURCE",t/"index.json"), \
                 patch.object(vision,"official_robots",side_effect=AssertionError("network accessed")), \
                 patch.object(vision,"download_pdf",side_effect=AssertionError("PDF downloaded")), \
                 patch.dict(os.environ,{"OPENAI_API_KEY":"fake"}):
                report=auto.run(["--archive-only"],today=TODAY)
                self.assertEqual(report["api_calls"],0)
                self.assertEqual(report["archived_this_run"],1)
                self.assertEqual(report["pending_review_count"],1)
                self.assertEqual(report["archived_count"],1)
                self.assertEqual(len(json.loads((t/"expired_archive.json").read_text())),1)
                self.assertEqual(len(json.loads((t/"pending.json").read_text())),1)
                again=auto.run(["--archive-only"],today=TODAY)
                self.assertEqual(again["archived_this_run"],0)

    def test_real_index_uploads_do_not_prove_event_dates(self):
        index={"programs":[doc(CASERONES),doc(OLD)]}
        self.assertEqual([e["pdf_url"] for e in p.sorted_programs(index,TODAY,{},[])],[CASERONES])

if __name__=="__main__":
    unittest.main()
