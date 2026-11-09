"""Static sponsor media is optimized only once without fetching remote content."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from optimize_static_sponsors import optimize

class StaticSponsorTests(unittest.TestCase):
    def test_downscales_one_approved_webp_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"sponsor.webp"
            image=Image.new("RGB",(324,500))
            px=image.load()
            for y in range(500):
                for x in range(324):
                    px[x,y]=((x*17+y*3)%256,(x*7+y*19)%256,(x*13+y*11)%256)
            image.save(path,format="WEBP",quality=95)
            before=path.stat().st_size
            self.assertTrue(optimize(path))
            self.assertLess(path.stat().st_size,before)
            with Image.open(path) as improved:
                self.assertLessEqual(improved.width,260)
                self.assertLessEqual(improved.height,400)
            self.assertFalse(optimize(path))

    def test_missing_file_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(optimize(Path(tmp)/"none.webp"))

if __name__=="__main__":
    unittest.main()
