import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from domains import load_psl  # noqa: E402
from vermarkter import account_index, owner_key, sales_path, site_vermarkter  # noqa: E402

PSL = load_psl()


def row(ssp, sid, domain, typ="PUBLISHER", conf="nein", name="N"):
    return {"ssp": ssp, "seller_id": sid, "domain_clean": domain, "seller_type": typ,
            "is_confidential": conf, "name": name}


INDEX = account_index([
    row("pubmatic", "1", "zeitung.de"),
    row("pubmatic", "2", "vermarkt.de"),
    row("openx", "3", "stroeer.com"),
    row("openx", "4", "google.com", "INTERMEDIARY"),
    row("magnite", "5", "", conf="ja", name=""),
    row("pubmatic", "7", "a.de", "INTERMEDIARY"),
    row("pubmatic", "7", "b.de", "PUBLISHER"),
])
GROUPS = {"stroeer.de": "stroeer", "stroeer.com": "stroeer"}


def line(ssp, sid, rel="DIRECT"):
    return {"ssp": ssp, "seller_id": sid, "relation": rel}


class SalesPathTests(unittest.TestCase):
    def path(self, ssp, sid, rel="DIRECT"):
        return sales_path("zeitung.de", rel, INDEX.get((ssp, sid)), PSL)

    def test_wege(self):
        self.assertEqual(self.path("pubmatic", "1"), "selbst")
        self.assertEqual(self.path("pubmatic", "2"), "vermarkter")
        self.assertEqual(self.path("pubmatic", "2", "RESELLER"), "reseller")
        self.assertEqual(self.path("openx", "4", "RESELLER"), "google")
        self.assertEqual(self.path("index-exchange", "9"), "unbekannt")

    def test_subdomain_des_kontos_ist_selbst(self):
        idx = account_index([row("openx", "8", "verlag.zeitung.de")])
        self.assertEqual(sales_path("zeitung.de", "DIRECT", idx[("openx", "8")], PSL), "selbst")

    def test_doppelte_id_publisher_gewinnt(self):
        self.assertEqual(INDEX[("pubmatic", "7")]["domain"], "b.de")


class OwnerTests(unittest.TestCase):
    def test_gruppe_und_vertraulich(self):
        self.assertEqual(owner_key(INDEX[("openx", "3")], GROUPS, PSL), "stroeer")
        self.assertEqual(owner_key(INDEX[("magnite", "5")], GROUPS, PSL), "vertraulich")
        self.assertEqual(owner_key(INDEX[("pubmatic", "2")], GROUPS, PSL), "vermarkt.de")

    def test_site_vermarkter(self):
        lines = [line("pubmatic", "1"), line("pubmatic", "2"), line("openx", "3"), line("magnite", "5"),
                 line("pubmatic", "2", "RESELLER"), line("index-exchange", "9")]
        self.assertEqual(site_vermarkter("zeitung.de", lines, INDEX, GROUPS, PSL),
                         ["stroeer", "vermarkt.de", "vertraulich"])


if __name__ == "__main__":
    unittest.main()
