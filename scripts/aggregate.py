"""Erzeugt aus dem Monats-Snapshot die kleinen Dateien für das Dashboard.

- data/aggregates/YYYY-MM.json: Zähltabellen und Auswertungen
"""
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOOGLE = "google.com"
CORRECTIONS = {"leerzeichen_entfernt", "schema_entfernt", "pfad_entfernt", "mehrere_domains",
               "kleinschreibung", "www_entfernt", "endpunkt_entfernt"}


def iter_snapshot(month):
    """Liefert die Zeilen des Snapshots nacheinander oder None, wenn es ihn nicht gibt."""
    p = ROOT / "data" / "snapshots" / f"{month}.csv.gz"
    if not p.exists():
        return None

    def gen():
        with gzip.open(p, "rt", newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)
    return gen()


def previous_month(month):
    y, m = map(int, month.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def direct_overlap(idx, ssps):
    """Überschneidung der direkt gelisteten Publisher: Domains mit mindestens einem PUBLISHER-Eintrag je SSP."""
    ids = [s["id"] for s in ssps]
    dom = {d: {k for k, v in e["ssps"].items() if "PUBLISHER" in v["types"]} for d, e in idx.items()}
    dom = {d: v for d, v in dom.items() if v}
    by = Counter(len(v) for v in dom.values())
    per = {}
    for i in ids:
        mine = [v for v in dom.values() if i in v]
        per[i] = {"n": len(mine), "exclusive": sum(1 for v in mine if len(v) == 1),
                  "few": sum(1 for v in mine if 2 <= len(v) <= 3), "many": sum(1 for v in mine if len(v) >= 4)}
    combos = Counter(tuple(i for i in ids if i in v) for v in dom.values() if len(v) >= 2)
    return {"domains": len(dom), "by_count": {str(k): by[k] for k in range(1, len(ids) + 1)}, "per_ssp": per,
            "combos": [{"ssps": list(k), "n": n} for k, n in combos.most_common(6)]}


def local_analysis(idx, ssps, tld):
    """Sonderauswertung für eine Länderendung: Zahl der Domains und deren direkte Überschneidung."""
    sub = {d: e for d, e in idx.items() if e["tld"] == tld}
    return {"tld": tld, "domains": len(sub), "direct": direct_overlap(sub, ssps)}


def build(month, rows, prev_rows, fetch_log, ssps):
    """Ein Durchlauf über die Zeilen. Gibt (Aggregat, Domain-Index) zurück."""
    ids = [s["id"] for s in ssps]
    cube = Counter()
    totals = Counter()
    corrected = Counter()
    flag_counts = {i: Counter() for i in ids}
    idx = {}
    cur_ids = defaultdict(set)
    for r in rows:
        ssp = r["ssp"]
        d = r["domain_clean"]
        cube[(ssp, r["seller_type"], r["tld"] or "unbekannt", r["is_confidential"], int(d == GOOGLE))] += 1
        totals[ssp] += 1
        cur_ids[ssp].add(r["seller_id"])
        fl = [f for f in r["flags"].split("|") if f]
        flag_counts[ssp].update(fl)
        if CORRECTIONS.intersection(fl):
            corrected[ssp] += 1
        if d:
            e = idx.setdefault(d, {"ssps": {}, "names": Counter(), "tld": r["tld"]})
            s = e["ssps"].setdefault(ssp, {"n": 0, "types": Counter(), "conf": Counter()})
            s["n"] += 1
            s["types"][r["seller_type"]] += 1
            s["conf"][r["is_confidential"]] += 1
            if r["name"]:
                e["names"][r["name"]] += 1

    overlap = Counter(len(e["ssps"]) for e in idx.values())

    changes = None
    if prev_rows is not None:
        before = defaultdict(set)
        for r in prev_rows:
            before[r["ssp"]].add(r["seller_id"])
        changes = {i: {"neu": len(cur_ids[i] - before[i]), "entfernt": len(before[i] - cur_ids[i])}
                   for i in ids if i in before}

    log = {e["ssp"]: e for e in fetch_log}
    n = len(ids)
    agg = {
        "month": month,
        "ssps": [{
            "id": s["id"], "name": s["name"], "url": s["url"], "color": s.get("color"), "short": s.get("short"), "sellers": totals[s["id"]],
            "fetched_at": log.get(s["id"], {}).get("fetched_at"), "bytes": log.get(s["id"], {}).get("bytes"),
            "sha256": log.get(s["id"], {}).get("sha256"),
        } for s in ssps],
        "cube": [{"ssp": a, "type": b, "tld": c, "conf": d, "g": g, "n": k} for (a, b, c, d, g), k in sorted(cube.items())],
        "overlap": {"by_count": {str(k): overlap[k] for k in range(1, n + 1)}, "unique_domains": len(idx)},
        "analysis": {"direct": direct_overlap(idx, ssps), "de": local_analysis(idx, ssps, "de")},
        "quality": {i: {"sellers": totals[i], "korrigiert": corrected[i],
                        "flags": dict(flag_counts[i])} for i in ids},
        "changes": changes,
    }
    return agg, idx


def main(month):
    ssps = json.loads((ROOT / "config" / "ssps.json").read_text(encoding="utf-8"))
    rows = iter_snapshot(month)
    if rows is None:
        sys.exit(f"Kein Snapshot für {month}. Erst clean.py ausführen.")
    log_p = ROOT / "data" / "raw" / month / "fetch_log.json"
    fetch_log = json.loads(log_p.read_text(encoding="utf-8")) if log_p.exists() else []
    agg, idx = build(month, rows, iter_snapshot(previous_month(month)), fetch_log, ssps)
    out = ROOT / "data" / "aggregates" / f"{month}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(agg, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    months = sorted(p.stem for p in out.parent.glob("????-??.json"))
    (out.parent / "index.json").write_text(json.dumps(months), encoding="utf-8")
    print(f"-> {out} ({out.stat().st_size} Bytes), {len(idx)} Domains")


if __name__ == "__main__":
    main(sys.argv[1])
