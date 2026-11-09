"""Static Cabildo poster optimization must not invent sources or fetch checkout pages."""
import datetime as dt
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_poster_thumbnails as posters

URL="https://www.eventosgrancanaria.com/controlpanel/files/gridfs/6a955c6a013a6268e0795f4b"
URL2="https://www.eventosgrancanaria.com/controlpanel/files/gridfs/6ab332eb013a6268e079e576"


def event(url=URL,date="2026-11-09",sponsored=False,status="official_remote"):
    return {"id":23,"title":"Concierto del Cabildo","start":date+"T20:00:00",
            "image_url":url,"image_status":status,
            "paid_promotion":sponsored,
            "image_origin":"Organizador · cartel oficial",
            "source_url":"https://www.eventosgrancanaria.com/event/1234"}


def sample_png(w=1280,h=860):
    buffer=BytesIO()
    image=Image.new("RGB",(w,h),(121,54,188))
    image.save(buffer,"PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self,data,status=200,headers=None):
        self.content=data
        self.text=(data.decode("utf-8") if isinstance(data,bytes) and
                   data.startswith(b"User-agent:") else "")
        self.status_code=status
        self.headers=headers or {"Content-Type":"image/png",
                                 "Content-Length":str(len(data))}
        self.closed=False
    def iter_content(self,chunk_size=131072):
        for i in range(0,len(self.content),chunk_size):
            yield self.content[i:i+chunk_size]
    def close(self):
        self.closed=True


class FakeSession:
    def __init__(self,allow=True,poster=None):
        self.calls=[]
        self.poster=poster or sample_png()
        self.allow=allow
    def get(self,url,**options):
        self.calls.append((url,options))
        if url.endswith("/robots.txt"):
            text="User-agent: *\n"+("" if self.allow else "Disallow: /controlpanel/files/gridfs/\n")
            return FakeResponse(text.encode(),headers={"Content-Type":"text/plain"})
        return FakeResponse(self.poster)


class PosterThumbnailTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,9,tzinfo=dt.timezone.utc)

    def test_only_verified_cabildo_gridfs_source_is_eligible(self):
        self.assertTrue(posters.valid_official_url(URL))
        for url in (
            URL+"?width=640",
            URL+"/../admin",
            URL.replace("https://","http://"),
            URL.replace("www.eventosgrancanaria.com","www.eventosgrancanaria.com.evil.test"),
            URL.replace("controlpanel/files/gridfs","checkout"),
            "file:///etc/passwd",
            "https://127.0.0.1/controlpanel/files/gridfs/6a955c6a013a6268e0795f4b",
        ):
            with self.subTest(url=url):
                self.assertFalse(posters.valid_official_url(url))
        self.assertEqual(posters.poster_filename(URL),"6a955c6a013a6268e0795f4b.webp")

    def test_long_running_programmes_get_thumbnails_until_verified_end(self):
        ongoing={**event(URL,date="2026-09-11"),"end":"2026-12-11"}
        finished={**event(URL2,date="2026-09-11"),"end":"2026-10-25"}
        upcoming={**event(URL2,date="2026-11-13"),"end":None}
        self.assertEqual(posters.candidates([finished,ongoing,upcoming],self.now),
                         [URL,URL2])

    def test_program_without_confirmed_end_is_not_assumed_active(self):
        previous=event(URL,date="2026-09-11")
        self.assertEqual(posters.candidates([previous],self.now),[])

    def test_no_sponsored_past_unconfirmed_or_other_host_poster(self):
        cases=[
            event(date="2026-11-10"),
            event(date="2026-11-02"),
            event(date="2026-11-10",sponsored=True),
            event(date="2026-11-10",status="unverified"),
            event(url="https://other.example/photo.png",date="2026-11-10"),
            event(date="2026-11-10"),
            event(url=URL2,date="2026-11-09"),
        ]
        self.assertEqual(posters.candidates(cases,self.now),[URL2,URL])

    def test_poster_is_resized_without_cropping_and_webp_is_small(self):
        raw=sample_png()
        out=posters.compress_webp(raw)
        self.assertLess(len(out),posters.MAX_WEBP_BYTES)
        with Image.open(BytesIO(out)) as image:
            self.assertEqual(image.format,"WEBP")
            self.assertEqual(image.size,(760,511))
            self.assertAlmostEqual(image.width/image.height,1280/860,delta=0.005)

    def test_denies_oversized_invalid_and_animated_sources(self):
        with self.assertRaises(ValueError):
            posters.compress_webp(b"0"*(posters.MAX_BYTES+1))
        with self.assertRaises(Exception):
            posters.compress_webp(b"not really an image")
        with Image.new("RGBA",(100,50),(20,30,40,120)) as img:
            b=BytesIO();img.save(b,"PNG")
            optimized=posters.compress_webp(b.getvalue())
            with Image.open(BytesIO(optimized)) as result:
                self.assertEqual(result.mode,"RGBA")

    def test_robots_policy_required_before_downloading(self):
        session=FakeSession(allow=False)
        with tempfile.TemporaryDirectory() as tmp:
            result=posters.generate([event()],Path(tmp),session,self.now,
                                    max_new=3,delay=0)
            self.assertEqual(result["available"],0)
            self.assertEqual(result["failures"],1)
            # The policy blocks image fetch: only robots.txt was requested.
            self.assertEqual(len(session.calls),1)
            self.assertTrue(session.calls[0][0].endswith("/robots.txt"))
            self.assertEqual(json.dumps(result).count("failure"),1)
            self.assertIn("Object.freeze({})",
                          (Path(tmp)/"manifest.js").read_text())

    def test_end_to_end_generates_only_safe_static_webp(self):
        session=FakeSession()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            rows=[event(),event(),event(sponsored=True)]
            results=posters.generate(rows,out,session,self.now,max_new=1,delay=0)
            self.assertEqual(results["new"],1)
            self.assertEqual(results["available"],1)
            self.assertEqual(len(session.calls),2)
            self.assertEqual(session.calls[-1][0],URL)
            self.assertFalse(any("checkout" in url for url,_ in session.calls))
            thumb=out/posters.poster_filename(URL)
            self.assertTrue(thumb.is_file())
            with Image.open(thumb) as image:
                self.assertEqual(image.format,"WEBP")
                self.assertLessEqual(image.width,760)
            text=(out/"manifest.js").read_text()
            self.assertIn(URL,text)
            self.assertIn("/posters/6a955c6a013a6268e0795f4b.webp",text)
            self.assertIn("Object.freeze(",text)

            # A second run reuses the immutable file without downloading it again.
            reuse=FakeSession()
            repeat=posters.generate(rows,out,reuse,self.now,max_new=1,delay=0)
            self.assertEqual(repeat["new"],0)
            self.assertEqual(repeat["available"],1)
            self.assertEqual(len(reuse.calls),1)

    def test_bounded_work_defers_unprocessed_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=posters.generate([event(URL),event(URL2)],Path(tmp),
                FakeSession(),self.now,max_new=1,delay=0)
            self.assertEqual(result["new"],1)
            self.assertEqual(result["available"],1)
            self.assertEqual(result["candidates"],2)

    def test_robots_unavailable_fails_closed(self):
        class Bad(FakeSession):
            def get(self,url,**opts):
                return FakeResponse(b"bad gateway",status=503)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,"robots.txt unavailable"):
                posters.generate([event()],Path(tmp),Bad(),self.now,delay=0)

    def test_manifest_never_injects_arbitrary_javascript(self):
        result=posters.manifest_content({
            URL:"/posters/6a955c6a013a6268e0795f4b.webp",
            URL2:"https://outside.example/evil.js",
            "https://evil.example/img":"/posters/6a955c6a013a6268e0795f4b.webp",
        })
        self.assertIn(URL,result)
        self.assertNotIn("outside.example",result)
        self.assertNotIn("evil.example",result)
        self.assertIn("Object.freeze(",result)


if __name__=="__main__":
    unittest.main()
