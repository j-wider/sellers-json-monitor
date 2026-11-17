import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from domains import host_from_origin, load_psl, registrable_domain  # noqa: E402

PSL = load_psl()


class RegistrableTests(unittest.TestCase):
    def test_www_und_m(self):
        for h in ("www.spiegel.de", "m.spiegel.de", "spiegel.de"):
            self.assertEqual(registrable_domain(h, PSL), "spiegel.de")

    def test_mehrteilige_endung(self):
        self.assertEqual(registrable_domain("m.bbc.co.uk", PSL), "bbc.co.uk")
        self.assertEqual(registrable_domain("shop.example.com.au", PSL), "example.com.au")

    def test_private_endung(self):
        self.assertEqual(registrable_domain("foo.github.io", PSL), "foo.github.io")

    def test_nur_endung(self):
        self.assertEqual(registrable_domain("co.uk", PSL), "")
        self.assertEqual(registrable_domain("de", PSL), "")

    def test_ungueltig(self):
        self.assertEqual(registrable_domain("", PSL), "")
        self.assertEqual(registrable_domain("localhost", PSL), "")

    def test_origin(self):
        self.assertEqual(host_from_origin("https://WWW.Spiegel.de:443/"), "www.spiegel.de")
        self.assertEqual(host_from_origin("http://example.de."), "example.de")


if __name__ == "__main__":
    unittest.main()
