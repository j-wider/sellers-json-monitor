"""Zerlegt die abgerufenen ads.txt-Dateien (IAB ads.txt 1.1)."""
import re

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
