"""Verkaufswege je ads.txt-Zeile und Vermarkter je Website.

Eine ads.txt-Zeile wird über (SSP, Seller-ID) im sellers.json-Snapshot desselben Monats nachgeschlagen.
"""
import json
from pathlib import Path

from domains import registrable_domain

ROOT = Path(__file__).resolve().parent.parent
GOOGLE = "google.com"
CONFIDENTIAL = "vertraulich"


def account_index(rows):
    """(ssp, seller_id) -> Konto. Bei doppelter ID gewinnt der erste PUBLISHER-Eintrag, sonst der erste."""
    idx = {}
    for r in rows:
        key = (r["ssp"], r["seller_id"])
        acc = {"domain": r["domain_clean"], "type": r["seller_type"], "name": r["name"],
               "confidential": r["is_confidential"] == "ja"}
        old = idx.get(key)
        if old is None or (old["type"] != "PUBLISHER" and acc["type"] == "PUBLISHER"):
            idx[key] = acc
    return idx


def sales_path(website, relation, account, psl):
    if account is None:
        return "unbekannt"
    if account["type"] == "INTERMEDIARY" and account["domain"] == GOOGLE:
        return "google"
    if account["domain"] and registrable_domain(account["domain"], psl) == website:
        return "selbst"
    if relation == "RESELLER":
        return "reseller"
    return "vermarkter"


def owner_key(account, groups, psl):
    if not account["domain"]:
        return CONFIDENTIAL
    d = registrable_domain(account["domain"], psl) or account["domain"]
    return groups.get(d, d)


def load_groups(path=None):
    """Gibt (Domain -> Gruppen-ID, Gruppen-ID -> Name) aus config/vermarkter.json zurück."""
    p = Path(path or ROOT / "config" / "vermarkter.json")
    if not p.exists():
        return {}, {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return ({d: g["id"] for g in data for d in g["domains"]}, {g["id"]: g["name"] for g in data})


def site_vermarkter(website, lines, index, groups, psl):
    owners = set()
    for ln in lines:
        acc = index.get((ln["ssp"], ln["seller_id"]))
        if sales_path(website, ln["relation"], acc, psl) == "vermarkter":
            owners.add(owner_key(acc, groups, psl))
    return sorted(owners)
