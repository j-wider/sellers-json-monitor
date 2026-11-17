"""Startliste: die in Deutschland meistgenutzten Websites laut Chrome-UX-Report (CrUX).

Quelle: github.com/zakird/crux-top-lists. Origins bis Rangstufe 10.000 werden auf die
Hauptdomain verdichtet, Erwachsenenseiten laut UT1-Liste (CC BY-SA 4.0) entfernt.

- data/crux/YYYY-MM.csv: domain, rank, crux_month
- data/crux/YYYY-MM.meta.json: CrUX-Monat, Quellen, Zahl der entfernten Domains
"""
import csv
import gzip
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from domains import host_from_origin, load_psl, registrable_domain

ROOT = Path(__file__).resolve().parent.parent
UA = "sellers-json-monitor/0.2 (+https://github.com/j-wider/sellers-json-monitor)"
CRUX_URL = "https://raw.githubusercontent.com/zakird/crux-top-lists/main/data/country/de/{}.csv.gz"
ADULT_URLS = [f"https://raw.githubusercontent.com/olbat/ut1-blacklists/master/blacklists/adult/domains.{i}"
              for i in range(3)]
MAX_RANK = 10000


def crux_candidates(month):
    """Vormonat bis drei Monate zurück, neueste zuerst. Google veröffentlicht um den zweiten Dienstag."""
    y, m = map(int, month.split("-"))
    out = []
    for _ in range(3):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        out.append(f"{y}{m:02d}")
    return out


def compress_origins(rows, psl, max_rank=MAX_RANK):
    best = {}
    for origin, rank in rows:
        if rank > max_rank:
            continue
        d = registrable_domain(host_from_origin(origin), psl)
        if d and rank < best.get(d, max_rank + 1):
            best[d] = rank
    return best


def adult_hits(lines, domains):
    """Domains der Startliste, die in der Liste stehen. Ein Eintrag sub.bar.de sperrt bar.de nicht."""
    hits = set()
    for line in lines:
        e = line.strip().lower()
        if e.startswith("www."):
            e = e[4:]
        if e in domains:
            hits.add(e)
    return hits


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120)


def _stream_lines(urls):
    """Liest die in Teile zerlegte Liste zeilenweise. Ein Teil kann mitten in einer Zeile enden."""
    rest = b""
    for url in urls:
        with _get(url) as r:
            while chunk := r.read(1 << 20):
                lines = (rest + chunk).split(b"\n")
                rest = lines.pop()
                for x in lines:
                    yield x.decode("utf-8", "replace")
    if rest:
        yield rest.decode("utf-8", "replace")


def load_crux(month):
    """Gibt (crux_month, url, rows) zurück oder wirft den letzten Fehler."""
    err = None
    for cm in crux_candidates(month):
        url = CRUX_URL.format(cm)
        try:
            with _get(url) as r:
                text = gzip.decompress(r.read()).decode("utf-8")
        except Exception as e:
            err = e
            continue
        rows = [(o, int(k)) for o, k in csv.reader(io.StringIO(text)) if k.isdigit()]
        return cm, url, rows
    raise err


def main(month):
    try:
        cm, url, rows = load_crux(month)
    except Exception as e:
        print(f"::warning::CrUX-Liste für {month} nicht abrufbar: {type(e).__name__}: {e}")
        return 2
    psl = load_psl()
    best = compress_origins(rows, psl)
    try:
        hits = adult_hits(_stream_lines(ADULT_URLS), set(best))
    except Exception as e:
        print(f"::warning::Erwachsenen-Liste nicht abrufbar: {type(e).__name__}: {e}")
        return 2
    kept = sorted(((d, r) for d, r in best.items() if d not in hits), key=lambda x: (x[1], x[0]))
    out = ROOT / "data" / "crux" / f"{month}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["domain", "rank", "crux_month"])
        w.writerows((d, r, cm) for d, r in kept)
    meta = {"crux_month": cm, "crux_url": url, "origins": len(rows),
            "domains_before_filter": len(best), "adult_removed": len(hits),
            "adult_source": "UT1 (Universität Toulouse Capitole, CC BY-SA 4.0) über github.com/olbat/ut1-blacklists",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out.parent / f"{month}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"CrUX {cm}: {len(best)} Hauptdomains, {len(hits)} entfernt, {len(kept)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
