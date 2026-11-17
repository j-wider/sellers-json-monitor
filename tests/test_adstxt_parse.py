import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from adstxt_parse import parse_adstxt  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_kommentare(self):
        p = parse_adstxt("# x\ngoogle.com, pub-1, DIRECT, f08c47fec0942fa0 # gut\n")
        self.assertEqual(p["records"], [{"system": "google.com", "seller_id": "pub-1",
                                         "relation": "DIRECT", "cert": "f08c47fec0942fa0"}])
        self.assertEqual(p["invalid"], 0)

    def test_bom_crlf_schreibweise(self):
        r = parse_adstxt("﻿PubMatic.com, 156, reseller\r\n")["records"][0]
        self.assertEqual((r["system"], r["seller_id"], r["relation"], r["cert"]), ("pubmatic.com", "156", "RESELLER", ""))

    def test_tabulatoren_und_fuehrende_null(self):
        self.assertEqual(parse_adstxt("appnexus.com,\t0123,\tDIRECT")["records"][0]["seller_id"], "0123")

    def test_seller_id_schreibweise_bleibt(self):
        self.assertEqual(parse_adstxt("openx.com, AbC9, DIRECT")["records"][0]["seller_id"], "AbC9")

    def test_variablen(self):
        p = parse_adstxt("OwnerDomain=spiegel.de\nMANAGERDOMAIN=iqdigital.de\ncontact=a@b.de\nsubdomain=m.x.de")
        self.assertEqual(p["records"], [])
        self.assertEqual(p["variables"], {"OWNERDOMAIN": ["spiegel.de"], "MANAGERDOMAIN": ["iqdigital.de"],
                                          "CONTACT": ["a@b.de"], "SUBDOMAIN": ["m.x.de"]})

    def test_platzhalter(self):
        p = parse_adstxt("placeholder.example.com, placeholder, DIRECT, placeholder\n")
        self.assertTrue(p["placeholder"])
        self.assertEqual(p["records"], [])

    def test_fehlerhafte_zeilen(self):
        p = parse_adstxt("nur.eins\na.com, 1, INDIRECT\na.com, , DIRECT\n")
        self.assertEqual((p["records"], p["invalid"]), ([], 3))

    def test_html(self):
        p = parse_adstxt("<!doctype html><html><body>Nicht gefunden</body></html>")
        self.assertEqual(p["records"], [])
        self.assertGreaterEqual(p["invalid"], 1)


if __name__ == "__main__":
    unittest.main()
