"""Hauptdomain (registrierbare Domain) über die Public Suffix List bestimmen.

www.spiegel.de und m.spiegel.de ergeben spiegel.de, m.bbc.co.uk ergibt bbc.co.uk.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PSL_PATH = ROOT / "config" / "public_suffix_list.dat"


def _ascii(rule):
    # Die Liste enthält Unicode-Endungen, Hosts kommen als Punycode.
    try:
        return rule.encode("idna").decode("ascii")
    except UnicodeError:
        return rule


def load_psl(path=None):
    rules, wild, exc = set(), set(), set()
    for line in Path(path or PSL_PATH).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        rule = line.split()[0].lower()
        if rule.startswith("!"):
            exc.add(_ascii(rule[1:]))
        elif rule.startswith("*."):
            wild.add(_ascii(rule[2:]))
        else:
            rules.add(_ascii(rule))
    return {"rules": rules, "wild": wild, "exc": exc}


def _suffix_len(labels, psl):
    """Zahl der Labels der öffentlichen Endung (längste passende Regel)."""
    n = len(labels)
    for i in range(n):
        cand = ".".join(labels[i:])
        if cand in psl["exc"]:
            return n - i - 1
        if cand in psl["rules"] or (i + 1 < n and ".".join(labels[i + 1:]) in psl["wild"]):
            return n - i
    return 1  # Standardregel "*": die letzte Stelle ist die Endung


def registrable_domain(host, psl):
    host = (host or "").strip().lower().rstrip(".")
    if not host:
        return ""
    labels = host.split(".")
    if any(not x for x in labels):
        return ""
    k = _suffix_len(labels, psl)
    if len(labels) <= k:
        return ""
    return ".".join(labels[-(k + 1):])


def host_from_origin(origin):
    h = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", (origin or "").strip())
    h = re.split(r"[/?#]", h, maxsplit=1)[0]
    h = re.sub(r":\d+$", "", h)
    return h.rstrip(".").lower()
