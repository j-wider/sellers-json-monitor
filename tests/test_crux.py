import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from crux import adult_hits, compress_origins, crux_candidates  # noqa: E402
from domains import load_psl  # noqa: E402

PSL = load_psl()


class CruxTests(unittest.TestCase):
    def test_kandidaten(self):
        self.assertEqual(crux_candidates("2026-12"), ["202611", "202610", "202609"])

    def test_kandidaten_jahreswechsel(self):
        self.assertEqual(crux_candidates("2027-01"), ["202612", "202611", "202610"])

    def test_verdichtung_beste_rangstufe(self):
        rows = [("https://www.spiegel.de", 5000), ("https://m.spiegel.de", 1000),
                ("https://x.de", 50000), ("http://bbc.co.uk", 10000)]
        self.assertEqual(compress_origins(rows, PSL), {"spiegel.de": 1000, "bbc.co.uk": 10000})

    def test_erwachsenenfilter(self):
        lines = ["foo.com\n", "sub.bar.de\n", "\n", "# x\n", "www.baz.net\r\n"]
        self.assertEqual(adult_hits(lines, {"foo.com", "bar.de", "baz.net", "spiegel.de"}), {"foo.com", "baz.net"})


if __name__ == "__main__":
    unittest.main()
