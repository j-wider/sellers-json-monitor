import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_adstxt import build_adstxt  # noqa: E402
from test_vermarkter import GROUPS, INDEX, PSL  # noqa: E402


def dom(d, r, e, n=0, res=0, status="gefunden"):
    return {"domain": d, "rank": str(r), "status": status, "einstufung": e, "lines_total": str(n),
            "reseller_lines": str(res), "systems": "1", "invalid": "0", "ownerdomain": "",
            "managerdomain": "stroeer.de" if d == "zeitung.de" else "", "contact": "", "subdomain": ""}


def ln(ssp, sid, rel="DIRECT"):
    return {"domain": "zeitung.de", "ssp": ssp, "seller_id": sid, "relation": rel, "cert": ""}


DOMAINS = [dom("zeitung.de", 1000, "werbung", 6, 1), dom("leer.de", 5000, "keine_werbung", status="keine_adstxt"),
           dom("zu.de", 10000, "nicht_abrufbar", status="blockiert")]
LINES = [ln("pubmatic", "1"), ln("pubmatic", "2"), ln("openx", "3"), ln("openx", "4", "RESELLER"),
         ln("magnite", "5"), ln("index-exchange", "9")]
META = {"crux_month": "202610", "adult_removed": 7}
LOG = {"started_at": "2026-11-17T18:00:00+00:00"}


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.agg = build_adstxt("2026-11", META, LOG, DOMAINS, LINES, INDEX, GROUPS, {"stroeer": "Ströer"}, PSL, None)

    def test_counts(self):
        self.assertEqual(self.agg["counts"], {"domains": 3, "werbung": 1, "keine_werbung": 1,
                                              "nicht_abrufbar": 1, "adult_removed": 7})
        self.assertEqual((self.agg["crux_month"], self.agg["fetched_at"]), ("202610", "2026-11-17T18:00:00+00:00"))

    def test_sites(self):
        s = {x["d"]: x for x in self.agg["sites"]}
        self.assertEqual(s["zeitung.de"]["v"], ["stroeer", "vermarkt.de", "vertraulich"])
        self.assertEqual(s["zeitung.de"]["mgr"], "stroeer.de")
        self.assertIn(["pubmatic", "1", "N", "selbst", "DIRECT"], s["zeitung.de"]["rows"])
        self.assertIn(["index-exchange", "9", "", "unbekannt", "DIRECT"], s["zeitung.de"]["rows"])
        self.assertEqual(s["zu.de"]["rows"], [])
        self.assertEqual(s["zu.de"]["e"], "nicht_abrufbar")

    def test_vermarkter(self):
        v = {x["id"]: x for x in self.agg["vermarkter"]}
        self.assertEqual((v["stroeer"]["name"], v["stroeer"]["sites"], v["stroeer"]["top1000"]), ("Ströer", 1, 1))
        self.assertEqual(v["stroeer"]["ssps"], {"openx": 1})
        self.assertEqual(v["stroeer"]["site_list"], [["zeitung.de", 1000]])

    def test_markt(self):
        m = self.agg["market"]
        # Je SSP zählt eine Website einmal, beim direktesten Verkaufsweg.
        self.assertEqual(m["10000"]["per_ssp"]["pubmatic"], {"alle": 1, "selbst": 1})
        self.assertEqual(m["10000"]["per_ssp"]["openx"], {"alle": 1, "vermarkter": 1})
        self.assertEqual(m["10000"]["share_ads"], 0.5)  # nicht abrufbare Domains zählen nicht zur Basis
        self.assertEqual(m["1000"]["share_ads"], 1.0)
        self.assertEqual(m["10000"]["median_lines"], 6)
        self.assertAlmostEqual(m["10000"]["reseller_share"], 1 / 6)
        self.assertIsNone(self.agg["prev"])


if __name__ == "__main__":
    unittest.main()
