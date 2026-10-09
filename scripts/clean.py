"""Bereinigt die Rohdaten und schreibt einen flachen Monats-Snapshot (CSV).

Originalwerte bleiben in *_raw-Spalten erhalten. Jede Korrektur erzeugt ein Flag.
"""
import csv
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["ssp", "seller_id", "name", "domain_raw", "domain_clean", "tld", "seller_type",
          "is_confidential", "is_passthrough", "flags"]
VALID_TYPES = {"PUBLISHER", "INTERMEDIARY", "BOTH"}
LABEL = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)$")
TLD = re.compile(r"^(?:[a-z]{2,24}|xn--[a-z0-9-]{2,59})$")


def clean_domain(raw):
    """Gibt (domain_clean, tld, flags) zurück. Fehlt die Domain, ist domain_clean leer."""
    flags = []
    if raw is None or not str(raw).strip():
        return "", "", ["domain_fehlt"]
    d = str(raw)
    if d != d.strip():
        flags.append("leerzeichen_entfernt")
    parts = re.split(r"[\s,;]+", d.strip())
    if len(parts) > 1:
        flags.append("mehrere_domains")
    d = parts[0]
    if "@" in d:
        return "", "", flags + ["domain_ungueltig"]
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", d):
        d = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", d)
        flags.append("schema_entfernt")
    if "/" in d or "?" in d or "#" in d:
        d = re.split(r"[/?#]", d, maxsplit=1)[0]
        flags.append("pfad_entfernt")
    d = re.sub(r":\d+$", "", d)
    if d.endswith("."):
        d = d.rstrip(".")
        flags.append("endpunkt_entfernt")
    if d != d.lower():
        d = d.lower()
        flags.append("kleinschreibung")
    if d.startswith("www."):
        d = d[4:]
        flags.append("www_entfernt")
    labels = d.split(".")
    if len(labels) < 2 or not all(LABEL.match(x) for x in labels) or not TLD.match(labels[-1]):
        return "", "", flags + ["domain_ungueltig"]
    return d, labels[-1], flags


def clean_bool(v):
    if v is None or v == "":
        return "nicht_angegeben"
    if str(v).strip().lower() in ("1", "true", "yes"):
        return "ja"
    if str(v).strip().lower() in ("0", "false", "no"):
        return "nein"
    return "nicht_angegeben"


def clean_seller(ssp, s):
    flags = []
    sid = str(s.get("seller_id", ""))
    if sid != sid.strip():
        flags.append("id_leerzeichen_entfernt")
    confidential = clean_bool(s.get("is_confidential")) == "ja"
    name = s.get("name")
    # Bei confidential-Sellern fehlen Name und Domain absichtlich, das ist kein Datenfehler.
    if (name is None or not str(name).strip()) and not confidential:
        flags.append("name_fehlt")
    dom, tld, dflags = clean_domain(s.get("domain"))
    flags += [f for f in dflags if not (f == "domain_fehlt" and confidential)]
    st = str(s.get("seller_type") or "").strip().upper()
    if st not in VALID_TYPES:
        flags.append("typ_unbekannt")
        st = "NICHT_ANGEGEBEN"
    return {
        "ssp": ssp, "seller_id": sid.strip(), "name": (name or "").strip(),
        "domain_raw": "" if s.get("domain") is None else s["domain"],
        "domain_clean": dom, "tld": tld, "seller_type": st,
        "is_confidential": clean_bool(s.get("is_confidential")),
        "is_passthrough": clean_bool(s.get("is_passthrough")),
        "flags": "|".join(flags),
    }


def clean_all(ssp, sellers):
    """Erzeugt die bereinigten Zeilen nacheinander (die Google-Datei hat fast eine Million Einträge)."""
    seen = Counter(str(s.get("seller_id", "")).strip() for s in sellers)
    for s in sellers:
        r = clean_seller(ssp, s)
        if seen[r["seller_id"]] > 1:
            r["flags"] = "|".join(filter(None, [r["flags"], "id_doppelt"]))
        yield r


def main(month):
    ssps = json.loads((ROOT / "config" / "ssps.json").read_text(encoding="utf-8"))
    out = ROOT / "data" / "snapshots" / f"{month}.csv.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with gzip.open(out, "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for ssp in ssps:
            p = ROOT / "data" / "raw" / month / f"{ssp['id']}.json.gz"
            if not p.exists():
                print(f"übersprungen (keine Rohdatei): {ssp['id']}")
                continue
            sellers = json.loads(gzip.decompress(p.read_bytes()))["sellers"]
            n = 0
            for r in clean_all(ssp["id"], sellers):
                w.writerow(r)
                n += 1
            total += n
            print(f"{ssp['id']}: {n} Zeilen")
            del sellers
    print(f"{total} Zeilen -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
