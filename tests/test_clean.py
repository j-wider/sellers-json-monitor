import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from clean import clean_all, clean_domain, clean_seller  # noqa: E402


class DomainTests(unittest.TestCase):
    def test_sauber(self):
        self.assertEqual(clean_domain("beispiel.de"), ("beispiel.de", "de", []))

    def test_leerzeichen(self):
        d, t, f = clean_domain(" beispiel.de ")
        self.assertEqual((d, t), ("beispiel.de", "de"))
        self.assertIn("leerzeichen_entfernt", f)

    def test_schema_pfad_schraegstrich(self):
        d, _, f = clean_domain("https://beispiel.de/seite/x/")
        self.assertEqual(d, "beispiel.de")
        self.assertIn("schema_entfernt", f)
        self.assertIn("pfad_entfernt", f)
        self.assertEqual(clean_domain("beispiel.at/")[0], "beispiel.at")

    def test_mehrere_domains(self):
        d, _, f = clean_domain("a.de b.com")
        self.assertEqual(d, "a.de")
        self.assertIn("mehrere_domains", f)

    def test_gross_und_www(self):
        d, _, f = clean_domain("WWW.Beispiel.CH")
        self.assertEqual(d, "beispiel.ch")
        self.assertIn("kleinschreibung", f)
        self.assertIn("www_entfernt", f)

    def test_fehlend(self):
        for v in (None, "", "  "):
            self.assertEqual(clean_domain(v), ("", "", ["domain_fehlt"]))

    def test_ungueltig(self):
        self.assertIn("domain_ungueltig", clean_domain("beispiel.comfr1")[2])  # Ziffern in Endung
        self.assertIn("domain_ungueltig", clean_domain("N/A")[2])
        self.assertIn("domain_ungueltig", clean_domain("mail@firma.de")[2])


class SellerTests(unittest.TestCase):
    def test_fehlende_felder_und_typ(self):
        r = clean_seller("x", {"seller_id": " 7 ", "seller_type": "NA"})
        self.assertEqual(r["seller_id"], "7")
        self.assertEqual(r["seller_type"], "NICHT_ANGEGEBEN")
        for f in ("name_fehlt", "domain_fehlt", "typ_unbekannt", "id_leerzeichen_entfernt"):
            self.assertIn(f, r["flags"])
        self.assertEqual(r["is_confidential"], "nicht_angegeben")

    def test_typ_schreibweise_und_original_bleibt(self):
        r = clean_seller("x", {"seller_id": "1", "name": "N", "domain": "Beispiel.de", "seller_type": "Both", "is_confidential": 1})
        self.assertEqual(r["seller_type"], "BOTH")
        self.assertEqual(r["domain_raw"], "Beispiel.de")
        self.assertEqual(r["is_confidential"], "ja")

    def test_dubletten(self):
        rows = list(clean_all("x", [{"seller_id": "1", "name": "a", "domain": "a.de", "seller_type": "PUBLISHER"}] * 2))
        self.assertTrue(all("id_doppelt" in r["flags"] for r in rows))

    def test_confidential_ohne_name_und_domain_ist_kein_fehler(self):
        r = clean_seller("x", {"seller_id": "pub-1", "is_confidential": 1, "seller_type": "PUBLISHER"})
        self.assertEqual(r["flags"], "")
        self.assertEqual(r["is_confidential"], "ja")
        self.assertEqual(r["domain_clean"], "")

    def test_nichtbreakendes_leerzeichen(self):
        d, _, f = clean_domain(" funkedigital.de")
        self.assertEqual(d, "funkedigital.de")
        self.assertIn("leerzeichen_entfernt", f)


if __name__ == "__main__":
    unittest.main()
