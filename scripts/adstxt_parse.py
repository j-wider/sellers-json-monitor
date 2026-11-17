"""Zerlegt die abgerufenen ads.txt-Dateien (IAB ads.txt 1.1).

- data/adstxt/YYYY-MM.csv.gz: eine Zeile je ads.txt-Zeile zu einer der sechs SSPs
- data/adstxt/YYYY-MM-domains.csv.gz: Zusammenfassung je Domain der Startliste
"""
import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINE_FIELDS = ["domain", "ssp", "seller_id", "relation", "cert"]
DOMAIN_FIELDS = ["domain", "rank", "status", "einstufung", "lines_total", "reseller_lines", "systems", "invalid",
                 "ownerdomain", "managerdomain", "contact", "subdomain"]

VARIABLES = ("OWNERDOMAIN", "MANAGERDOMAIN", "CONTACT", "SUBDOMAIN")
RELATIONS = {"DIRECT", "RESELLER"}
SYSTEM = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
PLACEHOLDER = ("placeholder.example.com", "placeholder", "DIRECT", "placeholder")


def parse_adstxt(text):
    records, invalid, placeholder = [], 0, False
    variables = {v: [] for v in VARIABLES}
    for line in text.lstrip("﻿").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        eq, comma = line.find("="), line.find(",")
        if eq > 0 and (comma < 0 or eq < comma):
            name, value = line[:eq].strip().upper(), line[eq + 1:].strip()
            if name in variables and value:
                variables[name].append(value)
            continue  # unbekannte Variablen sind laut Spezifikation erlaubt
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            invalid += 1
            continue
        system, sid, rel = parts[0].lower(), parts[1], parts[2].upper()
        cert = parts[3] if len(parts) > 3 else ""
        if (system, sid.lower(), rel, cert.lower()) == PLACEHOLDER:
            placeholder = True
            continue
        if not SYSTEM.match(system) or not sid or rel not in RELATIONS:
            invalid += 1
            continue
        records.append({"system": system, "seller_id": sid, "relation": rel, "cert": cert})
    return {"records": records, "variables": variables, "placeholder": placeholder, "invalid": invalid}


def ssp_lookup(ssps):
    """Systemdomain der ads.txt -> SSP-ID (adstxt_domain und optional adstxt_aliases)."""
    out = {}
    for s in ssps:
        for d in [s["adstxt_domain"], *s.get("adstxt_aliases", [])]:
            out[d.lower()] = s["id"]
    return out


def classify_site(status, parsed):
    if status in ("keine_adstxt", "fehlerseite"):
        return "keine_werbung"
    if status != "gefunden":
        return "nicht_abrufbar"
    return "werbung" if parsed["records"] else "keine_werbung"


def main(month):
    ssps = json.loads((ROOT / "config" / "ssps.json").read_text(encoding="utf-8"))
    lookup = ssp_lookup(ssps)
    with (ROOT / "data" / "crux" / f"{month}.csv").open(encoding="utf-8", newline="") as f:
        ranks = {r["domain"]: r["rank"] for r in csv.DictReader(f)}
    raw = ROOT / "data" / "raw" / month
    log = json.loads((raw / "adstxt_log.json").read_text(encoding="utf-8"))["domains"]
    texts = {}
    with gzip.open(raw / "adstxt.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            texts[x["domain"]] = x["text"]
    out = ROOT / "data" / "adstxt"
    out.mkdir(parents=True, exist_ok=True)
    unmatched, n_lines = Counter(), 0
    with gzip.open(out / f"{month}.csv.gz", "wt", newline="", encoding="utf-8") as fl, \
            gzip.open(out / f"{month}-domains.csv.gz", "wt", newline="", encoding="utf-8") as fd:
        wl, wd = csv.DictWriter(fl, LINE_FIELDS), csv.DictWriter(fd, DOMAIN_FIELDS)
        wl.writeheader()
        wd.writeheader()
        for e in log:
            d = e["domain"]
            p = parse_adstxt(texts[d]) if d in texts else None
            recs = p["records"] if p else []
            for r in recs:
                ssp = lookup.get(r["system"])
                if ssp:
                    wl.writerow({"domain": d, "ssp": ssp, "seller_id": r["seller_id"],
                                 "relation": r["relation"], "cert": r["cert"]})
                    n_lines += 1
                else:
                    unmatched[r["system"]] += 1
            v = p["variables"] if p else {}
            wd.writerow({"domain": d, "rank": ranks.get(d, ""), "status": e["status"],
                         "einstufung": classify_site(e["status"], p), "lines_total": len(recs),
                         "reseller_lines": sum(r["relation"] == "RESELLER" for r in recs),
                         "systems": len({r["system"] for r in recs}), "invalid": p["invalid"] if p else 0,
                         **{k.lower(): "|".join(v.get(k, [])) for k in VARIABLES}})
    print(f"{len(log)} Domains, {n_lines} Zeilen zu den SSPs -> {out}")
    print("Häufigste andere Systemdomains: " + ", ".join(f"{k} {n}" for k, n in unmatched.most_common(25)))


if __name__ == "__main__":
    main(sys.argv[1])
