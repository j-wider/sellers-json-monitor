"""Ruft die ads.txt jeder Domain der Startliste ab.

- data/raw/YYYY-MM/adstxt.jsonl.gz: Rohtext je gefundener Domain
- data/raw/YYYY-MM/adstxt_log.json: Status, Endadresse, Größe, SHA-256 je Domain

Weiterleitungen nach IAB ads.txt 1.1: Innerhalb der Hauptdomain beliebig viele Sprünge,
dazu höchstens ein Sprung auf eine fremde Domain, die selbst nicht mehr weiterleiten darf.
"""
import csv
import gzip
import hashlib
import http.client
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from domains import load_psl, registrable_domain

ROOT = Path(__file__).resolve().parent.parent
UA = "sellers-json-monitor/0.2 (+https://github.com/j-wider/sellers-json-monitor)"
WORKERS = 20
TIMEOUT = 10
MAX_BYTES = 2 * 1024 * 1024
MAX_HOPS = 5
# 308 ist gleichbedeutend mit 301 und wird deshalb wie 301, 302 und 307 behandelt.
REDIRECTS = {301, 302, 307, 308}
UNREACHABLE = {"blockiert", "zeitueberschreitung", "fehler"}
DEADLINE = 30  # Sekunden je Abruf insgesamt
CHUNK = 64 * 1024
# Von zwei Versuchen gilt das Ergebnis, das weiter vorn steht.
RANK = ["gefunden", "keine_adstxt", "fehlerseite", "blockiert", "zeitueberschreitung", "fehler"]


def redirect_allowed(domain, chain, psl):
    left = False
    for url in chain[1:]:
        if left:
            return False  # die fremde Adresse hat selbst weitergeleitet
        if registrable_domain(urlsplit(url).hostname or "", psl) != domain:
            left = True
    return True


def classify_response(http_status, content_type, body, error):
    if http_status is None:
        return "zeitueberschreitung" if error == "timeout" else "fehler"
    if http_status in (404, 410):
        return "keine_adstxt"
    if http_status in (401, 403, 429):
        return "blockiert"
    if http_status != 200 or error:
        return "fehler"
    text = body.strip()
    if not text:
        return "keine_adstxt"
    if "html" in (content_type or "").lower() or text.startswith(b"<"):
        return "fehlerseite"
    return "gefunden"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _request(url):
    """Gibt (status, content_type, body, location, error) zurück."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/plain, */*"})
    try:
        start = time.monotonic()
        with _OPENER.open(req, timeout=TIMEOUT) as r:
            # TIMEOUT gilt je Socket-Operation. Ein Server, der Bytes tröpfeln lässt, wird über die Gesamtfrist gestoppt.
            body = b""
            while len(body) < MAX_BYTES:
                if time.monotonic() - start > DEADLINE:
                    return None, "", b"", None, "timeout"
                chunk = r.read(min(CHUNK, MAX_BYTES - len(body)))
                if not chunk:
                    break
                body += chunk
            return r.status, r.headers.get("Content-Type", ""), body, None, None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), b"", e.headers.get("Location"), None
    except (TimeoutError, socket.timeout):
        return None, "", b"", None, "timeout"
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            return None, "", b"", None, "timeout"
        return None, "", b"", None, f"{type(e.reason).__name__}: {e.reason}"
    except (ssl.SSLError, OSError, ValueError, http.client.HTTPException) as e:
        return None, "", b"", None, f"{type(e).__name__}: {e}"


def _fetch_url(domain, url, psl):
    chain = [url]
    while True:
        status, ctype, body, location, error = _request(chain[-1])
        if status in REDIRECTS and location:
            chain.append(urljoin(chain[-1], location))
            if len(chain) > MAX_HOPS + 1:
                return chain, None, "", b"", "zu viele Weiterleitungen"
            if not redirect_allowed(domain, chain, psl):
                return chain, None, "", b"", "Weiterleitung nicht erlaubt"
            continue
        return chain, status, ctype, body, error


def fetch_domain(domain, psl):
    """Versucht DOMAIN und, falls nötig, www.DOMAIN. Behalten wird das aussagekräftigere Ergebnis."""
    attempts = []
    try:
        for url in (f"https://{domain}/ads.txt", f"https://www.{domain}/ads.txt"):
            chain, status, ctype, body, error = _fetch_url(domain, url, psl)
            attempts.append((classify_response(status, ctype, body, error), url, chain, status, body, error))
            if attempts[-1][0] in ("gefunden", "keine_adstxt"):
                break
    except Exception as e:  # ein einzelner kaputter Server darf den Monatslauf nicht abbrechen
        url = f"https://{domain}/ads.txt"
        attempts.append(("fehler", url, [url], None, b"", f"{type(e).__name__}: {e}"))
    result, url, chain, status, body, error = min(attempts, key=lambda a: RANK.index(a[0]))
    entry = {"domain": domain, "status": result, "url": url, "final_url": chain[-1], "http_status": status,
             "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest() if body else None,
             "redirects": len(chain) - 1, "detail": error, "first_status": attempts[0][0],
             "www_status": attempts[1][0] if len(attempts) > 1 else None}
    text = body.decode("utf-8", "replace") if result == "gefunden" else None
    return entry, text


def main(month, limit=None):
    src = ROOT / "data" / "crux" / f"{month}.csv"
    if not src.exists():
        sys.exit(f"Keine Startliste für {month}. Erst crux.py ausführen.")
    with src.open(encoding="utf-8", newline="") as f:
        domains = [r["domain"] for r in csv.DictReader(f)]
    if limit:
        domains = domains[:limit]
    psl = load_psl()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = sorted(ex.map(lambda d: fetch_domain(d, psl), domains), key=lambda x: x[0]["domain"])
    out = ROOT / "data" / "raw" / month
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / "adstxt.jsonl.gz", "wt", encoding="utf-8") as f:
        for e, text in results:
            if text is not None:
                f.write(json.dumps({"domain": e["domain"], "text": text}, ensure_ascii=False) + "\n")
    log = {"started_at": started, "domains": [e for e, _ in results]}
    (out / "adstxt_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = {}
    for e, _ in results:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    print(f"{len(results)} Domains: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    bad = sum(v for k, v in counts.items() if k in UNREACHABLE)
    if results and bad / len(results) > 0.3:
        print(f"::warning::{bad} von {len(results)} Domains nicht abrufbar (über 30 %).")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    lim = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    sys.exit(main(args[0], lim))
