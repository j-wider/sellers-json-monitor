"""Erzeugt data/aggregates/YYYY-MM-adstxt.json für die Reiter Vermarkter, Website-Suche und Marktkennzahlen."""
import csv
import gzip
import json
import statistics
import sys
from collections import Counter, defaultdict

from aggregate import iter_snapshot, previous_month
from domains import load_psl, registrable_domain
from vermarkter import CONFIDENTIAL, ROOT, account_index, load_groups, owner_key, sales_path

TIERS = (1000, 5000, 10000)


def _market(sites):
    reachable = [s for s in sites if s["e"] != "nicht_abrufbar"]
    ads = [s for s in sites if s["e"] == "werbung"]
    lines = sum(s["n"] for s in ads)
    per_ssp = defaultdict(Counter)
    for s in ads:
        paths = defaultdict(set)
        for ssp, _, _, path, _ in s["rows"]:
            paths[ssp].add(path)
        for ssp, ps in paths.items():
            per_ssp[ssp]["alle"] += 1
            per_ssp[ssp].update(ps)
    return {"domains": len(sites), "nicht_abrufbar": len(sites) - len(reachable), "werbung": len(ads),
            "share_ads": len(ads) / len(reachable) if reachable else None,
            "median_lines": statistics.median(s["n"] for s in ads) if ads else None,
            "reseller_share": sum(s["res"] for s in ads) / lines if lines else None,
            "per_ssp": {k: dict(v) for k, v in sorted(per_ssp.items())}}


def build_adstxt(month, crux_meta, fetch_log, domain_rows, line_rows, index, groups, names, psl, prev):
    lines_by_site = defaultdict(list)
    for ln in line_rows:
        lines_by_site[ln["domain"]].append(ln)
    sites, vm = [], {}
    for r in domain_rows:
        d, rank = r["domain"], int(r["rank"])
        rows, owners = [], set()
        for ln in lines_by_site.get(d, []) if r["einstufung"] == "werbung" else []:
            acc = index.get((ln["ssp"], ln["seller_id"]))
            path = sales_path(d, ln["relation"], acc, psl)
            rows.append([ln["ssp"], ln["seller_id"], acc["name"] if acc else "", path, ln["relation"]])
            if path == "vermarkter":
                key = owner_key(acc, groups, psl)
                owners.add(key)
                v = vm.setdefault(key, {"id": key, "domains": set(), "names": Counter(), "sites": {}, "ssps": defaultdict(set)})
                if acc["domain"]:
                    v["domains"].add(registrable_domain(acc["domain"], psl) or acc["domain"])
                if acc["name"]:
                    v["names"][acc["name"]] += 1
                v["sites"][d] = rank
                v["ssps"][ln["ssp"]].add(d)
        sites.append({"d": d, "r": rank, "s": r["status"], "e": r["einstufung"], "n": int(r["lines_total"]),
                      "res": int(r["reseller_lines"]), "own": r["ownerdomain"], "mgr": r["managerdomain"],
                      "v": sorted(owners), "rows": rows})
    vermarkter = []
    for key, v in vm.items():
        name = names.get(key) or ("Vertraulich (ohne Domain)" if key == CONFIDENTIAL else
                                  (v["names"].most_common(1)[0][0] if v["names"] else key))
        site_list = sorted(([d, r] for d, r in v["sites"].items()), key=lambda x: (x[1], x[0]))
        vermarkter.append({"id": key, "name": name, "domains": sorted(v["domains"]), "sites": len(site_list),
                           "top1000": sum(1 for _, r in site_list if r <= 1000),
                           "ssps": {s: len(ds) for s, ds in sorted(v["ssps"].items())}, "site_list": site_list})
    vermarkter.sort(key=lambda x: (x["id"] == CONFIDENTIAL, -x["sites"], x["id"]))
    counts = Counter(s["e"] for s in sites)
    return {
        "month": month, "crux_month": crux_meta["crux_month"], "fetched_at": fetch_log["started_at"],
        "counts": {"domains": len(sites), "werbung": counts["werbung"], "keine_werbung": counts["keine_werbung"],
                   "nicht_abrufbar": counts["nicht_abrufbar"], "adult_removed": crux_meta["adult_removed"]},
        "sites": sites, "vermarkter": vermarkter,
        "market": {str(t): _market([s for s in sites if s["r"] <= t]) for t in TIERS},
        "prev": prev["market"] if prev else None,
    }


def _csv(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(month):
    crux = ROOT / "data" / "crux" / f"{month}.meta.json"
    if not crux.exists():
        print(f"::warning::Keine ads.txt-Daten für {month}, Aggregat übersprungen.")
        return 0
    rows = iter_snapshot(month)
    if rows is None:
        sys.exit(f"Kein Snapshot für {month}. Erst clean.py ausführen.")
    psl = load_psl()
    groups, names = load_groups()
    agg_dir = ROOT / "data" / "aggregates"
    prev_p = agg_dir / f"{previous_month(month)}-adstxt.json"
    agg = build_adstxt(
        month, json.loads(crux.read_text(encoding="utf-8")),
        json.loads((ROOT / "data" / "raw" / month / "adstxt_log.json").read_text(encoding="utf-8")),
        _csv(ROOT / "data" / "adstxt" / f"{month}-domains.csv.gz"), _csv(ROOT / "data" / "adstxt" / f"{month}.csv.gz"),
        account_index(rows), groups, names, psl,
        json.loads(prev_p.read_text(encoding="utf-8")) if prev_p.exists() else None)
    out = agg_dir / f"{month}-adstxt.json"
    out.write_text(json.dumps(agg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"-> {out} ({out.stat().st_size} Bytes), {len(agg['vermarkter'])} Vermarkter")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
