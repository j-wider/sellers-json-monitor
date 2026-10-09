"""Lädt die sellers.json jeder SSP aus config/ssps.json und speichert sie gzip-komprimiert."""
import gzip
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "sellers-json-monitor/0.1 (private research project)"


def fetch_one(ssp, month):
    out = ROOT / "data" / "raw" / month / f"{ssp['id']}.json.gz"
    entry = {"ssp": ssp["id"], "url": ssp["url"], "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        req = urllib.request.Request(ssp["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            entry.update(status=r.status, final_url=r.geturl(), bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        json.loads(body)  # muss gültiges JSON sein
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(gzip.compress(body))
        entry["ok"] = True
    except Exception as e:
        entry.update(ok=False, error=f"{type(e).__name__}: {e}")
    return entry


def main(month=None, only=()):
    """only: optional SSP-IDs. Dann werden nur diese abgerufen, der Rest des Logs bleibt erhalten."""
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    ssps = json.loads((ROOT / "config" / "ssps.json").read_text(encoding="utf-8"))
    log_path = ROOT / "data" / "raw" / month / "fetch_log.json"
    old = json.loads(log_path.read_text(encoding="utf-8")) if only and log_path.exists() else []
    fresh = [fetch_one(s, month) for s in ssps if not only or s["id"] in only]
    log = [e for e in old if e["ssp"] not in {f["ssp"] for f in fresh}] + fresh
    order = {s["id"]: i for i, s in enumerate(ssps)}
    log.sort(key=lambda e: order.get(e["ssp"], 99))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    for e in fresh:
        print(f"{'OK  ' if e['ok'] else 'FEHLER'} {e['ssp']}: " + (f"{e['bytes']} Bytes" if e["ok"] else e["error"]))
    return 0 if all(e["ok"] for e in fresh) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None, sys.argv[2:]))
