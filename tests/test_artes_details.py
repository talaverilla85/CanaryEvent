import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from artes_details import parse_detail,apply_detail

class ArtsDetailsTest(unittest.TestCase):
 def test_venue_price_duration_clean_synopsis(self):
    html="""<html><div class="evento_ubicacion">Las Palmas de Gran Canaria<div class="tagselecteddark">Teatro Cuyás</div></div>
      <div class="evento_seccion">Sinopsis</div>
      S24 OCTUBRE, 19.30H<br/>31 FESTIVAL MASDANZA<br/>TRANSEÚNTE de Daniel Rodríguez<br/>
      Dirección y coreografía: Daniel Rodríguez.<br/>
      TRANSEÚNTE es un espectáculo es un espectáculo con seis intérpretes en escena, dos de los cuales también son músicos.<br/>
      DANZA<br/>DURACIÓN: 50 min.<br/>PRECIO ÚNICO: 10€<br/>ESPECTÁCULO SIN DESCUENTO
      <div><div>pie de página</div></div>
    </html>"""
    d=parse_detail(BeautifulSoup(html,"html.parser"))
    self.assertEqual(d["venue"],"Teatro Cuyás")
    self.assertEqual(d["price"],"10 €")
    self.assertEqual(d["free"],0)
    self.assertEqual(d["duration_min"],50)
    self.assertIn("seis intérpretes",d["details"])
    self.assertNotIn("S24 OCTUBRE",d["details"])
    e={"start":"2026-10-24T19:30:00","end":None,"venue":"sin recinto","details":"", "price":"", "free":None}
    apply_detail(e,d)
    self.assertEqual(e["end"],"2026-10-24T20:20:00")
    self.assertEqual(e["venue"],"Teatro Cuyás")
    self.assertEqual(e["price"],"10 €")

 def test_unknown_price_is_not_invented(self):
    html="""<div class="evento_ubicacion">Ingenio <div class="tagselecteddark">Centro Cultural</div></div>
      <div class="evento_seccion">Sinopsis</div>Un espectáculo familiar de teatro musical con participación del público y juegos.<br/>
      DURACIÓN: 75 min.<br/>ESPECTÁCULO SIN DESCUENTO<div class="footer">Contacto</div>"""
    d=parse_detail(BeautifulSoup(html,"html.parser"))
    self.assertEqual(d["price"],"")
    self.assertIsNone(d["free"])
    self.assertEqual(d["duration_min"],75)

 def test_windows_1252_euro_encoded_as_control(self):
    s=BeautifulSoup('<div class="evento_seccion">Sinopsis</div>PRECIO ÚNICO: 10\x80<div>F</div>',"html.parser")
    self.assertEqual(parse_detail(s)["price"],"10 €")

if __name__=="__main__":unittest.main()
