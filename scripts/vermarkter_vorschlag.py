"""Schlägt eine erste Fassung von config/vermarkter.json vor.

Zählt die Besitzer-Domains aller DIRECT-Konten mit Verkaufsweg "vermarkter" und fasst Domains
mit gleichem ersten Namensbestandteil laut sellers.json zu Gruppen zusammen. Das Ergebnis
ist ein Entwurf, der von Hand geprüft wird.

Aufruf: python scripts/vermarkter_vorschlag.py YYYY-MM [--schreiben]
"""
import csv
import gzip
import json
import re
import sys
from collections import Counter, defaultdict

from aggregate import iter_snapshot
from domains import load_psl, registrable_domain
from vermarkter import ROOT, account_index, sales_path

FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "é": "e"})
LEGAL = {"gmbh", "ag", "kg", "co", "se", "sa", "sas", "sl", "srl", "bv", "b", "v", "ltd", "limited", "inc", "llc",
         "spa", "s", "p", "a", "z", "o", "sp", "as", "ab", "plc", "the", "und"}


def name_key(name):
    """Firmenname ohne Rechtsform, z. B. "Yieldlove GmbH" und "yieldlove" ergeben "yieldlove"."""
    words = [w for w in re.split(r"[^a-z0-9]+", name.lower().translate(FOLD)) if w and w not in LEGAL]
    k = "".join(words)
    return k if len(k) >= 5 else ""


def domain_stem(domain, psl):
    """stroeer.de und stroeer.com ergeben "stroeer"."""
    reg = registrable_domain(domain, psl) or domain
    return reg.split(".")[0]


def cluster(owners, keys):
    """Fasst Besitzer zusammen, die mindestens einen Schlüssel teilen (Union-Find)."""
    parent = {o: o for o in owners}

    def root(o):
        while parent[o] != o:
            parent[o] = parent[parent[o]]
            o = parent[o]
        return o
    first = {}
    for o in owners:
        for k in keys[o]:
            if k in first:
                parent[root(o)] = root(first[k])
            else:
                first[k] = o
    out = defaultdict(list)
    for o in owners:
        out[root(o)].append(o)
    return [g for g in out.values() if len(g) > 1]


def main(month, write=False):
    psl = load_psl()
    index = account_index(iter_snapshot(month))
    sites, names = defaultdict(set), defaultdict(Counter)
    with gzip.open(ROOT / "data" / "adstxt" / f"{month}.csv.gz", "rt", encoding="utf-8", newline="") as f:
        for ln in csv.DictReader(f):
            acc = index.get((ln["ssp"], ln["seller_id"]))
            if acc and acc["domain"] and sales_path(ln["domain"], ln["relation"], acc, psl) == "vermarkter":
                owner = registrable_domain(acc["domain"], psl) or acc["domain"]
                sites[owner].add(ln["domain"])
                if acc["name"]:
                    names[owner][acc["name"]] += 1
    # Google-Konten tragen oft den Namen des Publishers und würden fremde Häuser verbinden.
    keys = {o: set() if domain_stem(o, psl) == "google" else
            {"d:" + domain_stem(o, psl)} | {"n:" + k for k in map(name_key, names[o]) if k} for o in sites}
    groups = []
    for owners in cluster(list(sites), keys):
        owners.sort(key=lambda o: -len(sites[o]))
        top = owners[0]
        groups.append({"id": domain_stem(top, psl), "name": names[top].most_common(1)[0][0] if names[top] else top,
                       "domains": owners})
    groups.sort(key=lambda g: -len(set().union(*(sites[d] for d in g["domains"]))))
    group_of = {d: g["id"] for g in groups for d in g["domains"]}

    print(f"{'Websites':>8}  {'Besitzer-Domain':<32} {'Name laut sellers.json':<40} Gruppe")
    for owner in sorted(sites, key=lambda o: -len(sites[o]))[:40]:
        nm = names[owner].most_common(1)[0][0] if names[owner] else ""
        print(f"{len(sites[owner]):>8}  {owner:<32} {nm[:40]:<40} {group_of.get(owner, '')}")
    print(f"\n{len(groups)} Gruppen vorgeschlagen:")
    for g in groups:
        print(f"  {g['id']}: {g['name']} <- {', '.join(g['domains'])}")
    if write:
        p = ROOT / "config" / "vermarkter.json"
        p.write_text(json.dumps(groups, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {p}")


if __name__ == "__main__":
    main(sys.argv[1], "--schreiben" in sys.argv)
