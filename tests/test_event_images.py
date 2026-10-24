import sqlite3
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import event_images as im
import sync_events as app
import cabildo_public as cb

class ImageTests(unittest.TestCase):
    def test_valid_official_image_urls_only(self):
        u="https://ingenio.es/wp-content/uploads/2026/10/cartel-300x300.jpg"
        self.assertEqual(im.image_url(u,"https://ingenio.es/events/"),u)
        self.assertEqual(im.image_url("/plot/event_4-1.jpg?fp=abc","https://artesescenicasgrancanaria.com/agenda.html"),
          "https://artesescenicasgrancanaria.com/plot/event_4-1.jpg?fp=abc")
        self.assertTrue(im.image_url("https://www.eventosgrancanaria.com/controlpanel/files/gridfs/abcdef123","https://www.eventosgrancanaria.com/"))
        for raw in ["https://images.unsplash.com/photo-1234","javascript:alert(1)","https://eventos.aguimes.es/storage/categories/cine.svg",
                    "https://www.eventosgrancanaria.com/og-image.jpg",
                    "http://ingenio.es/wp-content/uploads/foto.jpg",
                    "https://ingenio.es/favicon.jpg"]:
            self.assertEqual(im.image_url(raw,"https://ingenio.es/"),"",raw)

    def test_listing_img_over_category_logo(self):
        soup=BeautifulSoup("""<div class="event">
          <img src="/storage/categories/cine.svg">
          <img class="image" src="/storage/events/cartel.webp">
          </div>""","html.parser")
        u=im.listing_image(soup,"https://eventos.aguimes.es/",["img.image"])
        self.assertEqual(u,"https://eventos.aguimes.es/storage/events/cartel.webp")

    def test_cabildo_no_favicon_as_event_cover(self):
        soup=BeautifulSoup("""<meta property="og:image" content="https://www.eventosgrancanaria.com/og-image.jpg">
        <div class="event-detail__wrapper-image"><img src="/controlpanel/files/gridfs/123456"></div>""","html.parser")
        u=im.official_page_image(soup,"https://www.eventosgrancanaria.com/event/E-20261024-0001/something")
        self.assertEqual(u,"https://www.eventosgrancanaria.com/controlpanel/files/gridfs/123456")

    def test_database_migration_and_cover_upsert(self):
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory=sqlite3.Row
            app.init(conn)
            cols={row[1] for row in conn.execute("PRAGMA table_info(events)")}
            self.assertIn("image_url",cols)
            self.assertIn("image_origin",cols)
            d={
                "title":"Concierto en Ingenio","start":app.TODAY.isoformat()+"T19:00:00","end":None,
                "municipality":"Ingenio","venue":"Teatro","category":"musica","free":None,
                "price":"","details":"","source_name":"Ayuntamiento de Ingenio",
                "source_url":"https://ingenio.es/events/concierto/","status":"approved"
            }
            d.update(im.image_fields("https://ingenio.es/wp-content/uploads/concierto.jpg",d["title"],d["source_name"]))
            self.assertEqual(app.upsert(conn,d),"added")
            self.assertEqual(app.upsert(conn,d),"unchanged")
            e=conn.execute("SELECT * FROM events").fetchone()
            self.assertEqual(e["image_status"],"official_remote")
            self.assertIn("concierto.jpg",e["image_url"])
            d["image_url"]="https://ingenio.es/wp-content/uploads/segunda.jpg"
            self.assertEqual(app.upsert(conn,d),"changed")

if __name__=="__main__": unittest.main()
