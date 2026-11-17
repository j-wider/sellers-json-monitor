import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from adstxt_fetch import classify_response, redirect_allowed  # noqa: E402
from domains import load_psl  # noqa: E402

PSL = load_psl()


class RedirectTests(unittest.TestCase):
    def test_gleiche_hauptdomain(self):
        self.assertTrue(redirect_allowed("bild.de", ["http://bild.de/ads.txt", "https://www.bild.de/ads.txt"], PSL))

    def test_mehrere_spruenge_gleiche_hauptdomain(self):
        self.assertTrue(redirect_allowed("bild.de", ["http://bild.de/ads.txt", "https://bild.de/ads.txt",
                                                     "https://www.bild.de/ads.txt"], PSL))

    def test_ein_sprung_fremd(self):
        self.assertTrue(redirect_allowed("a.de", ["https://a.de/ads.txt", "https://cdn.fremd.net/a/ads.txt"], PSL))

    def test_zweiter_sprung_nach_fremd(self):
        self.assertFalse(redirect_allowed("a.de", ["https://a.de/ads.txt", "https://fremd.net/ads.txt",
                                                   "https://www.fremd.net/ads.txt"], PSL))

    def test_erst_intern_dann_fremd(self):
        self.assertTrue(redirect_allowed("a.de", ["http://a.de/ads.txt", "https://www.a.de/ads.txt",
                                                  "https://fremd.net/ads.txt"], PSL))


class StatusTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(classify_response(404, "text/html", b"", None), "keine_adstxt")
        self.assertEqual(classify_response(200, "text/plain", b"  \n", None), "keine_adstxt")
        self.assertEqual(classify_response(200, "text/html; charset=utf-8", b"<html>", None), "fehlerseite")
        self.assertEqual(classify_response(200, "text/plain", b"\n <!DOCTYPE html>", None), "fehlerseite")
        self.assertEqual(classify_response(403, "", b"", None), "blockiert")
        self.assertEqual(classify_response(429, "", b"", None), "blockiert")
        self.assertEqual(classify_response(None, "", b"", "timeout"), "zeitueberschreitung")
        self.assertEqual(classify_response(None, "", b"", "SSLError"), "fehler")
        self.assertEqual(classify_response(500, "", b"", None), "fehler")
        self.assertEqual(classify_response(200, "text/plain", b"a.com, 1, DIRECT", None), "gefunden")
        self.assertEqual(classify_response(200, "", b"a.com, 1, DIRECT", None), "gefunden")


if __name__ == "__main__":
    unittest.main()
