"""Regression checks for an early, automated official featured poster."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import sync_feature_preview as feature

HASH="a"*24
SRC="/posters/"+HASH+"-320.webp"
ORIGINAL="https://www.eventosgrancanaria.com/controlpanel/files/gridfs/"+HASH
HTML=(
    "<head>\n"+feature.START_PRELOAD+"\n"+feature.END_PRELOAD+"\n</head>"
    "<div id='feature'>"+feature.START_IMAGE+"\n"+feature.END_IMAGE+"</div>"
)

class FeaturePreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/(HASH+"-320.webp")).write_bytes(b"webp-test-stub")
        self.event={"id":101,"title":'Taller "Creativo" & cultura',
                    "start":"2026-10-01","end":"2026-12-01",
                    "image_status":"official_remote","image_url":ORIGINAL}

    def tearDown(self):
        self.temp.cleanup()

    def test_verified_local_preview_only(self):
        mapping={ORIGINAL:{"thumb":SRC,"detail":"/posters/"+HASH+".webp"}}
        rendered=feature.update(HTML,[self.event],mapping,self.root,"2026-11-09")
        self.assertIn('<link rel="preload" as="image" href="'+SRC+'"',rendered)
        self.assertIn('fetchpriority="high"',rendered)
        self.assertIn('src="'+SRC+'"',rendered)
        self.assertIn('Taller &quot;Creativo&quot; &amp; cultura',rendered)
        self.assertIn('data-feature-preview-date="2026-11-09"',rendered)
        self.assertEqual(feature.update(rendered,[self.event],mapping,self.root,
                                        "2026-11-09"),rendered)

    def test_stale_paid_missing_and_invalid_paths_never_preload(self):
        mapping={ORIGINAL:{"thumb":SRC}}
        bad_path={ORIGINAL:{"thumb":"https://external.example/image.jpg"}}
        for events,links,day in (
            ([self.event],mapping,"2027-01-01"),
            ([dict(self.event,paid_promotion=True)],mapping,"2026-11-09"),
            ([self.event],bad_path,"2026-11-09"),
            ([dict(self.event,image_status="unknown")],mapping,"2026-11-09"),
        ):
            with self.subTest(events=events,day=day):
                result=feature.update(HTML,events,links,self.root,day)
                self.assertNotIn('rel="preload"',result)
                self.assertNotIn('data-feature-preview-id',result)
        (self.root/(HASH+"-320.webp")).unlink()
        self.assertIsNone(feature.choose([self.event],mapping,self.root,"2026-11-09"))

    def test_no_duplicate_markers_or_invalid_html(self):
        with self.assertRaises(ValueError):
            feature.update(HTML.replace(feature.END_PRELOAD,""),
                           [self.event],{},self.root,"2026-11-09")
        with self.assertRaises(ValueError):
            feature.update(HTML+feature.START_IMAGE,
                           [self.event],{},self.root,"2026-11-09")

    def test_actual_home_has_synchronized_markers(self):
        html=(ROOT/"public/index.html").read_text(encoding="utf-8-sig")
        self.assertEqual(html.count(feature.START_PRELOAD),1)
        self.assertEqual(html.count(feature.END_PRELOAD),1)
        self.assertEqual(html.count(feature.START_IMAGE),1)
        self.assertEqual(html.count(feature.END_IMAGE),1)
        self.assertIn("function discardOutdatedFeaturedPreview()",html)
        self.assertIn("initial.getAttribute('src')===image",html)

if __name__=="__main__":
    unittest.main()
