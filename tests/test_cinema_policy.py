"""Routine commercial screening removal without harming cultural cinema."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import cinema_policy
CAB="Portal oficial de Eventos Gran Canaria (Cabildo)"

def entry(title,venue="Centro Comercial Siete Palmas",source=CAB,category="ocio"):
 return {"title":title,"venue":venue,"source_name":source,"category":category,
         "start":"2026-10-29T19:00:00","municipality":"Las Palmas de Gran Canaria"}

class CinemaPolicyTest(unittest.TestCase):
 def test_multiplex_routine_movies_filtered_even_if_cultura(self):
  for t in ["Clayface (ATMOS)","Resident Evil","Sentido y sensibilidad (VOSE)",
            "Superthings: La película (KIDS)","Dune Parte Tres (ATMOS)"]:
   self.assertTrue(cinema_policy.is_commercial_screening(entry(t)))
   self.assertTrue(cinema_policy.is_commercial_screening(entry(t,category="cultura")))
 def test_special_screenings_retained_even_inside_multiplex(self):
  specials=["Efecto cinema: El tren fluvial","Ciclo de cine Miradas Audiovisuales",
    "Festival de cine en Gran Canaria","Cine al aire libre: El viaje",
    "Preestreno de la película","Estreno especial de la película",
    "Debate y coloquio tras proyección","Concierto BTS WORLD TOUR LIVE VIEWING",
    "Stray Kids World Tour LIVE VIEWING (Reemisión)"]
  for title in specials:
   with self.subTest(title=title):
    self.assertFalse(cinema_policy.is_commercial_screening(entry(title)))
 def test_cultural_venues_and_non_cinema_activity_remain(self):
  for e in [
   entry("Alcarràs",venue="Teatro Guiniguada"),
   entry("Cine de Terror",venue="Centro comercial Atlántico"),
   entry("Feria artesanal local"),
   entry("Taller creativo con niños"),
   entry("NOCHE EN UN BAR",venue="Centro Cultural El Cine"),
   entry("Resident Evil",source="Ayuntamiento de Agüimes"),
   entry("Efecto cinema: LA NOCHE DE LOS MUERTOS VIVIENTES",venue="Yelmo cine Las Arenas")]:
   with self.subTest(title=e["title"]):
    self.assertFalse(cinema_policy.is_commercial_screening(e))
 def test_normalization_protects_accents(self):
  self.assertFalse(cinema_policy.is_commercial_screening(entry("Proyección especial: música en directo")))
  self.assertTrue(cinema_policy.is_commercial_screening(entry("Dune Parte Tres",venue="Cines Yelmo Las Arenas")))
 def test_existing_catalog_has_commercial_items_to_remove(self):
  es=json.loads((ROOT/"public/events.json").read_text(encoding="utf8"))["events"]
  kept,discarded=cinema_policy.remove_commercial_screenings(es)
  self.assertTrue(all(cinema_policy.is_commercial_screening(e) for e in discarded))
  self.assertEqual(len(kept)+len(discarded),len(es))
  self.assertTrue(any("Efecto cinema" in e["title"] for e in kept))
  self.assertTrue(any("Stray Kids" in e["title"] for e in kept))
  self.assertFalse(any("Clayface" in e["title"] for e in kept))
if __name__=="__main__":unittest.main()

