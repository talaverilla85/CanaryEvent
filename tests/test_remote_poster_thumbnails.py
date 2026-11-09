"""Official remote poster cache must obey allowlist, robots, and limits."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import build_remote_poster_thumbnails as remote

URL="https://eventos.santabrigida.es/wp-content/uploads/2026/09/WhatsApp-Image-2026-09-28-at-09.36.38.jpeg"
NOW=datetime(2026,11,9)
def event(url=URL):
    return {"id":123,"title":"Taller cultural","image_url":url,
            "image_status":"official_remote","paid_promotion":False,
            "start":"2026-10-01","end":"2026-11-30"}

def large_jpeg():
    image=Image.new("RGB",(1000,1000))
    pixels=image.load()
    for y in range(1000):
        for x in range(1000):
            pixels[x,y]=((x*17+y*3)%256,(x*7+y*19)%256,(x*13+y*11)%256)
    out=BytesIO()
    image.save(out,format="JPEG",quality=95)
    return out.getvalue()

class FakeResponse:
    def __init__(self,content=b"",status=200,mime="image/jpeg"):
        self.status_code=status
        self.headers={"Content-Type":mime,"Content-Length":str(len(content))}
        self.text=content.decode("utf8","replace") if mime=="text/plain" else ""
        self.content=content
    def iter_content(self,chunk_size=131072):
        for i in range(0,len(self.content),chunk_size):
            yield self.content[i:i+chunk_size]
    def close(self):
        pass

class FakeSession:
    def __init__(self,allow=True,source=None):
        self.allow=allow
        self.source=source or large_jpeg()
        self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if url.endswith("/robots.txt"):
            rule=b"User-agent: *\\nAllow: /wp-content/uploads/\\n"
            if not self.allow:
                rule=b"User-agent: *\\nDisallow: /wp-content/uploads/\\n"
            return FakeResponse(rule,mime="text/plain")
        return FakeResponse(self.source)

class RemotePosterTests(unittest.TestCase):
    def test_whitelist_blocks_spoofing_and_arbitrary_downloads(self):
        self.assertTrue(remote.valid_official_url(URL))
        for url in [
            "https://eventos.santabrigida.es.evil.com/wp-content/uploads/2026/09/foo.jpeg",
            "https://eventos.santabrigida.es/admin/settings.jpeg",
            "http://eventos.santabrigida.es/wp-content/uploads/2026/09/foo.jpeg",
            "https://eventos.santabrigida.es/wp-content/uploads/2026/09/foo.jpeg?token=secret",
            "https://eventos.santabrigida.es/wp-content/uploads/2026/09/../private/foo.jpeg",
            "https://ingenio.es:8443/wp-content/uploads/2026/09/foo.jpeg"
        ]:
            with self.subTest(url=url):
                self.assertFalse(remote.valid_official_url(url))
        self.assertEqual(remote.candidates([dict(event(),paid_promotion=True)],NOW),[])

    def test_can_make_small_static_versions_and_reuse_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess=FakeSession()
            first=remote.generate([event()],tmp,sess,NOW,max_new=1,delay=0)
            self.assertEqual(first["available"],1)
            self.assertEqual(first["new"],1)
            self.assertGreater(first["original_bytes"],first["variants_bytes"])
            names=remote.filenames(URL)
            for key,name in names.items():
                path=Path(tmp)/name
                self.assertTrue(path.is_file())
                with Image.open(path) as img:
                    self.assertEqual(img.format,"WEBP")
                    self.assertLessEqual(img.width,key if isinstance(key,int) else 760)
            manifest=(Path(tmp)/"remote-manifest.js").read_text()
            self.assertIn(remote.poster_id(URL)+"-320.webp",manifest)
            self.assertIn(URL,manifest)
            self.assertEqual(len(sess.calls),2)
            self.assertTrue(all(not args.get("allow_redirects",True) for _,args in sess.calls))
            again=FakeSession()
            second=remote.generate([event()],tmp,again,NOW,max_new=0,delay=0)
            self.assertEqual(second["available"],1)
            self.assertEqual(second["new"],0)
            self.assertEqual(len(again.calls),1,"Cached images must not be redownloaded")

    def test_robots_disallow_fails_closed_without_external_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess=FakeSession(allow=False)
            result=remote.generate([event()],tmp,sess,NOW,max_new=1,delay=0)
            self.assertEqual(result["available"],0)
            self.assertEqual(len(sess.calls),1)
            self.assertFalse(list(Path(tmp).glob("r-*.webp")))

    def test_manifest_rejects_other_paths_and_sources(self):
        paths={"thumb":"/posters/evil.webp","retina":"/posters/evil.webp",
               "detail":"/posters/evil.webp"}
        result=remote.manifest_content({URL:paths,"https://evil.invalid/a.png":paths})
        self.assertNotIn("evil.webp",result)
        self.assertNotIn("evil.invalid",result)

if __name__=="__main__":
    unittest.main()
