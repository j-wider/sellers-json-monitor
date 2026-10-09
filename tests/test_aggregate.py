import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from aggregate import build  # noqa: E402

SSPS = [{"id": "a", "name": "A", "url": ""}, {"id": "b", "name": "B", "url": ""}, {"id": "c", "name": "C", "url": ""}]


def row(ssp, domain, typ, name="N", conf="nicht_angegeben"):
    tld = domain.rsplit(".", 1)[-1] if domain else ""
    return {"ssp": ssp, "seller_id": "1", "name": name, "domain_raw": domain, "domain_clean": domain, "tld": tld,
            "seller_type": typ, "is_confidential": conf, "is_passthrough": "nicht_angegeben", "flags": ""}


class AggregateTests(unittest.TestCase):
    def setUp(self):
        rows = [
            row("a", "x.de", "INTERMEDIARY"), row("b", "x.de", "INTERMEDIARY"), row("c", "x.de", "INTERMEDIARY"),
            row("a", "y.com", "PUBLISHER"), row("b", "y.com", "INTERMEDIARY"),
            row("a", "z.com", "PUBLISHER"), row("a", "z.com", "INTERMEDIARY"),
            row("a", "google.com", "PUBLISHER"), row("a", "google.com", "PUBLISHER"),
        ]
        self.d, _ = build("2026-10", rows, None, [], SSPS)

    def test_eintraege_und_google(self):
        self.assertEqual(sum(r["n"] for r in self.d["cube"]), 9)
        self.assertEqual(sum(r["n"] for r in self.d["cube"] if r["g"]), 2)

    def test_direkte_ueberschneidung(self):
        d = self.d["analysis"]["direct"]
        # Publisher-Domains: y.com (a), z.com (a), google.com (a). x.de ist überall INTERMEDIARY. y.com bei b nur Intermediary.
        self.assertEqual(d["domains"], 3)
        self.assertEqual(d["by_count"], {"1": 3, "2": 0, "3": 0})
        self.assertEqual(d["per_ssp"]["a"], {"n": 3, "exclusive": 3, "few": 0, "many": 0})
        self.assertEqual(d["per_ssp"]["b"]["n"], 0)

    def test_kombinationen(self):
        rows = [row("a", "p.de", "PUBLISHER"), row("b", "p.de", "PUBLISHER"), row("c", "p.de", "BOTH"),
                row("a", "q.de", "PUBLISHER"), row("b", "q.de", "PUBLISHER"), row("c", "q.de", "PUBLISHER"),
                row("a", "r.de", "PUBLISHER"), row("b", "r.de", "PUBLISHER")]
        d, _ = build("2026-10", rows, None, [], SSPS)
        dd = d["analysis"]["direct"]
        self.assertEqual(dd["combos"][0], {"ssps": ["a", "b"], "n": 2})  # p.de (nur a, b als PUBLISHER) und r.de
        self.assertEqual(dd["combos"][1], {"ssps": ["a", "b", "c"], "n": 1})
        self.assertEqual(dd["per_ssp"]["a"], {"n": 3, "exclusive": 0, "few": 3, "many": 0})

    def test_sonderauswertung_de(self):
        de = self.d["analysis"]["de"]
        self.assertEqual(de["domains"], 1)  # nur x.de
        self.assertEqual(de["direct"]["domains"], 0)  # x.de ist überall INTERMEDIARY
        rows = [row("a", "p.de", "PUBLISHER"), row("b", "p.de", "PUBLISHER"), row("a", "q.de", "PUBLISHER"),
                row("a", "w.com", "PUBLISHER"), row("b", "w.com", "PUBLISHER")]
        d, _ = build("2026-10", rows, None, [], SSPS)
        de = d["analysis"]["de"]
        self.assertEqual(de["domains"], 2)
        self.assertEqual(de["direct"]["by_count"], {"1": 1, "2": 1, "3": 0})  # w.com zählt nicht

    def test_ueberschneidung_nach_anzahl(self):
        self.assertEqual(self.d["overlap"]["by_count"], {"1": 2, "2": 1, "3": 1})


if __name__ == "__main__":
    unittest.main()
