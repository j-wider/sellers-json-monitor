import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import http.client  # noqa: E402
from unittest import mock  # noqa: E402

import adstxt_fetch  # noqa: E402
from adstxt_fetch import classify_response, fetch_domain, redirect_allowed  # noqa: E402
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


class RobustnessTests(unittest.TestCase):
    def test_kaputte_http_antwort_bricht_nicht_ab(self):
        with mock.patch.object(adstxt_fetch._OPENER, "open", side_effect=http.client.BadStatusLine("GARBAGE")):
            entry, text = fetch_domain("kaputt.de", PSL)
        self.assertEqual(entry["status"], "fehler")
        self.assertIsNone(text)

    def test_unerwarteter_fehler_wird_fehler(self):
        with mock.patch.object(adstxt_fetch, "_fetch_url", side_effect=RuntimeError("x")):
            entry, _ = fetch_domain("x.de", PSL)
        self.assertEqual(entry["status"], "fehler")

    def test_gesamtfrist_je_abruf(self):
        class Slow:
            status, headers = 200, {"Content-Type": "text/plain"}
            def read(self, n=-1):
                return b"a.com, 1, DIRECT\n"
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        clock = iter(range(0, 10000, 5))
        with mock.patch.object(adstxt_fetch._OPENER, "open", return_value=Slow()), \
                mock.patch.object(adstxt_fetch.time, "monotonic", side_effect=lambda: next(clock)):
            entry, _ = fetch_domain("langsam.de", PSL)
        self.assertEqual(entry["status"], "zeitueberschreitung")

    def test_besseres_erstes_ergebnis_bleibt(self):
        res = {"https://a.de/ads.txt": (["https://a.de/ads.txt"], 200, "text/html", b"<html>", None),
               "https://www.a.de/ads.txt": (["https://www.a.de/ads.txt"], None, "", b"", "gaierror: DNS")}
        with mock.patch.object(adstxt_fetch, "_fetch_url", side_effect=lambda d, u, p: res[u]):
            entry, _ = fetch_domain("a.de", PSL)
        self.assertEqual((entry["status"], entry["url"]), ("fehlerseite", "https://a.de/ads.txt"))
        self.assertEqual(entry["first_status"], "fehlerseite")
        self.assertEqual(entry["www_status"], "fehler")


if __name__ == "__main__":
    unittest.main()
