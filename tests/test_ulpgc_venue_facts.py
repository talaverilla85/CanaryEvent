import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import ulpgc_venue_facts as u

class UlpgcVenueTests(unittest.TestCase):
    def entry(self,**overrides):
        row={
          "title":"Campaña de hemodonación: Facultad de Ciencias del Mar",
          "start":"2026-10-27T18:30:00", "end":None,
          "venue":"Consultar el recinto en la ficha oficial",
          "category":"ocio", "details":"Actividad en Las Palmas de Gran Canaria.",
          "organizer_url":"https://www.ulpgc.es/agenda/2026/10/26/campana-hemodonacion-facultad-ciencias-del-mar"
        }
        row.update(overrides)
        return row
    def test_verified_daily_hours_and_location(self):
        original=self.entry()
        result=u.enhance(original)
        self.assertEqual(result["venue"],"Facultad de Ciencias del Mar")
        self.assertEqual(result["start"],"2026-10-27T09:00:00")
        self.assertEqual(result["end"],"2026-10-27T18:30:00")
        self.assertIn("26 oct: 09:30–19:45",result["details"])
        self.assertIn("27 oct: 09:00–18:30",result["details"])
        self.assertEqual(original["start"],"2026-10-27T18:30:00")
        self.assertEqual(result["category"],"otros")

    def test_general_building_from_explicit_official_title(self):
        row=self.entry(title="Campaña de hemodonación: Facultad de Veterinaria",
                       start="2026-11-04T19:30:00")
        result=u.enhance(row)
        self.assertEqual(result["venue"],"Facultad de Veterinaria")
        self.assertEqual(result["start"],"2026-11-04")
        self.assertIsNone(result["end"])

    def test_unrelated_organizer_not_enriched(self):
        row=self.entry(organizer_url="https://example.com/agenda/2026/10/26/fake")
        self.assertEqual(u.enhance(row),row)

    def test_only_ulpgc_agenda_on_https_accepted(self):
        for url in ("http://www.ulpgc.es/agenda/2026/10/26/test",
                    "https://www.ulpgc.es.evil.example/agenda/2026/10/26/test",
                    "https://www.ulpgc.es/admin/credentials",
                    "https://www.ulpgc.es/agenda/2026/10/26/test?x=1"):
            self.assertFalse(u.safe_organizer(url))
        self.assertTrue(u.safe_organizer(self.entry()["organizer_url"]))

    def test_no_guessing_venue_if_title_unrelated(self):
        row=self.entry(title="Bodas de sangre")
        self.assertEqual(u.enhance(row),row)
        row=self.entry(title="Campaña de hemodonación: ¡Ven a donar!")
        self.assertEqual(u.enhance(row),row)

    def test_existing_verified_venue_is_preserved(self):
        row=self.entry(venue="Facultad de Ciencias del Mar (Campus de Tafira)")
        self.assertIn("Campus de Tafira",u.enhance(row)["venue"])

if __name__=="__main__":unittest.main()
