import json
import sqlite3
import sys
import unittest
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import event_enrichment as mod

DESCRIPTION = (
    "La compañía presenta un espectáculo de teatro y danza en Gran Canaria. "
    "El programa reúne música en directo, interpretaciones y una presentación "
    "especial en el recinto municipal con acceso organizado por la sala."
)
ROW = {
    "id": 1001, "status": "approved", "title": "La noche de las artes",
    "start": "2026-12-05", "end": None,
    "municipality": "Ingenio", "venue": "Lugar por confirmar",
    "details": "Consulta detalles en la fuente.", "source_url": "https://ingenio.es/events/la-noche-de-las-artes/",
    "organizer_url": "", "image_status": "not_available", "image_url": "",
    "price": "", "free": None, "updated_at": "2026-11-21T00:00:00"
}

def evidence_soup(title="La noche de las artes", day="2026-12-05"):
    return BeautifulSoup(
        '<html><script type="application/ld+json">'
        + json.dumps({
            "@context":"https://schema.org", "@type":"Event",
            "name":title, "startDate":day+"T20:00:00+00:00",
            "location":{"@type":"Place","name":"Teatro Federico García Lorca"},
            "description":DESCRIPTION
        })+'</script></html>', "html.parser")

def database():
    conn=sqlite3.connect(":memory:")
    conn.row_factory=sqlite3.Row
    conn.execute("""CREATE TABLE events (
      id INTEGER PRIMARY KEY,status TEXT,title TEXT,start TEXT,"end" TEXT,
      municipality TEXT,venue TEXT,details TEXT,source_url TEXT,
      organizer_url TEXT,image_status TEXT,image_url TEXT,
      price TEXT,free INTEGER,updated_at TEXT)""")
    keys=list(ROW)
    conn.execute(
        "INSERT INTO events("+",".join('"'+key+'"' for key in keys)+") VALUES("+",".join(["?"]*len(keys))+")",
        tuple(ROW.values())
    )
    return conn

class EventEnrichmentTests(unittest.TestCase):
    def test_detects_missing_metadata_separately(self):
        missing=mod.gaps(ROW)
        self.assertIn("recinto",missing)
        self.assertIn("descripcion",missing)
        self.assertIn("hora",missing)
        self.assertIn("cartel",missing)
        self.assertIn("precio",missing)

    def test_provenance_and_host_restrictions(self):
        event={**ROW,"organizer_url":"https://ingenio.es/events/other-source/"}
        links=mod.candidate_sources(event,[{
            "municipality":"Ingenio","label":"La noche de las artes",
            "url":"https://ingenio.es/events/another-event/"
        }])
        self.assertEqual(len(links),3)
        self.assertEqual(links[0],event["organizer_url"])
        self.assertEqual(mod.trusted_url("https://example.net/a"),"")
        self.assertEqual(mod.trusted_url("http://ingenio.es/events"),"")
        self.assertEqual(mod.trusted_url("https://ingenio.es@evil.example/events"),"")

    def test_only_matching_title_and_date_provides_facts(self):
        self.assertTrue(mod.structured_evidence(ROW,evidence_soup()))
        self.assertEqual(mod.structured_evidence(ROW,evidence_soup(day="2026-12-06")),{})
        self.assertEqual(mod.structured_evidence(ROW,evidence_soup(title="Festival distinto")),{})
        result=mod.structured_evidence(ROW,evidence_soup())
        self.assertEqual(result["venue"],"Teatro Federico García Lorca")
        self.assertTrue(result["start"].startswith("2026-12-05T20:00"))
        self.assertIn("compañía",result["details"])

    def test_verified_enrichment_keeps_original_id_and_evidence(self):
        conn=database()
        fetched=[]
        def fetch(url):
            fetched.append(url)
            return evidence_soup()
        result=mod.enrich(conn,"2026-11-21T23:12:00",date(2026,11,21),fetch_html=fetch,max_requests=2)
        self.assertEqual(result["verified"],1)
        record=conn.execute("SELECT * FROM events WHERE id=1001").fetchone()
        self.assertEqual(record["id"],1001)
        self.assertEqual(record["venue"],"Teatro Federico García Lorca")
        self.assertEqual(record["start"],"2026-12-05T20:00:00")
        self.assertTrue(mod.meaningful_description(record["details"]))
        audit=conn.execute("SELECT * FROM event_enrichment_checks WHERE event_id=1001").fetchone()
        self.assertEqual(audit["evidence_url"],ROW["source_url"])
        self.assertEqual(audit["original_source"],ROW["source_url"])
        self.assertEqual(audit["outcome"],"verified")
        proof=conn.execute("SELECT * FROM event_enrichment_proofs WHERE event_id=1001 AND field_name='venue'").fetchone()
        self.assertEqual(proof["evidence_url"],ROW["source_url"])
        self.assertEqual(proof["verified_value"],"Teatro Federico García Lorca")
        self.assertIn("descripcion",result["missing_by_field"])
        self.assertEqual(len(fetched),1)
        again=mod.enrich(conn,"2026-11-22T01:00:00",date(2026,11,21),fetch_html=fetch)
        self.assertEqual(again["requests"],0)
        self.assertEqual(len(fetched),1)

    def test_failed_source_does_not_make_up_details(self):
        conn=database()
        result=mod.enrich(conn,"2026-11-21T23:12:00",date(2026,11,21),
                          fetch_html=lambda url:evidence_soup(day="2026-12-06"),max_requests=1)
        self.assertEqual(result["verified"],0)
        item=conn.execute("SELECT * FROM events WHERE id=1001").fetchone()
        self.assertEqual(item["venue"],"Lugar por confirmar")
        self.assertEqual(item["start"],"2026-12-05")
        audit=conn.execute("SELECT outcome FROM event_enrichment_checks WHERE event_id=1001").fetchone()
        self.assertEqual(audit["outcome"],"no_matching_evidence")

    def test_limits_number_of_source_fetches(self):
        conn=database()
        for x in range(1002,1025):
            conn.execute("INSERT INTO events SELECT ?, status, title, start, \"end\", municipality, venue, details, source_url||?, organizer_url, image_status, image_url, price, free, updated_at FROM events WHERE id=1001",(x,str(x)))
        result=mod.enrich(conn,"2026-11-21T23:12:00",date(2026,11,21),
                          fetch_html=lambda url: evidence_soup(day="2026-12-06"),max_requests=3)
        self.assertEqual(result["requests"],3)

if __name__=="__main__":
    unittest.main()
