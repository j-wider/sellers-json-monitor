# sellers.json Monitor

Ruft die öffentlichen sellers.json-Dateien von sechs SSPs ab (PubMatic, Magnite, Index Exchange, OpenX, Equativ, Microsoft Monetize), bereinigt die Einträge und zeigt Rollenverhältnis, Überschneidung direkt gelisteter Publisher und eine Sonderauswertung für .de-Domains in einem Dashboard. Die Auswertung beschreibt nur, sie bewertet nichts.

## Ablauf

Monat als `YYYY-MM` angeben (hier Oktober 2026):

```bash
python scripts/fetch.py 2026-10
```

Optional nur einzelne SSPs abrufen (Rest des Logs bleibt erhalten), z. B. `python scripts/fetch.py 2026-10 openx adform`. Weiter:

```bash
python scripts/clean.py 2026-10
python scripts/aggregate.py 2026-10
```

Dashboard starten und im Browser öffnen:

```bash
python -m http.server 8765
```

Dann `http://localhost:8765/site/` aufrufen.

Tests für die Bereinigung:

```bash
python -m unittest discover -s tests -v
```

## Was wo liegt

| Ordner | Inhalt |
|---|---|
| `config/ssps.json` | Liste der SSPs mit URL, Farbe und Kürzel. Ein weiterer Eintrag nimmt eine weitere SSP auf. |
| `data/raw/YYYY-MM/` | Rohdateien (gzip) und `fetch_log.json` mit Abrufzeit, Größe und SHA-256. |
| `data/snapshots/YYYY-MM.csv.gz` | Eine Zeile pro Seller (gzip), Originalwerte (`domain_raw`) und bereinigte Werte nebeneinander. |
| `data/aggregates/YYYY-MM.json` | Zähltabellen und Auswertungen, die das Dashboard lädt. |
| `site/` | Dashboard (HTML, CSS, JS). D3 und d3-sankey liegen lokal in `site/vendor/`. |

## Bereinigung

Pro Korrektur setzt `clean.py` ein Flag im Snapshot: Leerzeichen entfernt, Schema (`https://`) entfernt, Pfad entfernt, mehrere Domains (erste wird genutzt), Kleinschreibung, `www.` entfernt, Domain fehlt oder ungültig, Name fehlt, Typ unbekannt, Seller-ID doppelt. Einträge werden nie gelöscht. Bei Einträgen mit `is_confidential` fehlen Name und Domain absichtlich, das zählt nicht als Fehler.

Die Länderendung ist der letzte Teil der bereinigten Domain (`example.co.uk` ergibt `uk`).

## Zählweise

- Gezählt werden Seller-Einträge, also Zeilen der sellers.json.
- Ein Eintrag mit Typ Intermediary und der Domain `google.com` gilt als Weg über Google-Bidding (Exchange Bidding, Open Bidding). Die Hauptgrafik blendet diese Einträge zu Beginn aus, der Schalter über der Grafik zeigt sie.
- „Direkt gelistet“: mindestens ein Eintrag der Domain hat den Typ Publisher.
- Die Überschneidung zählt Domains, nicht Einträge.
- Die Sonderauswertung nimmt alle Domains mit der Endung `.de`. Die Basis ist klein (rund 85 Domains).
- Microsoft Monetize (früher Xandr): Abruf über `appnexus.com/sellers.json`, das auf `acdn.adnxs.com` weiterleitet.
- Nicht aufgenommen, weil nicht passend oder zu groß: Google (Datei mit fast einer Million Einträgen), Improve Digital, Adform.

## Automatischer Monatslauf

Die GitHub Action `Monatslauf` läuft am 1. jedes Monats um 06:00 UTC und lässt sich unter „Actions“ von Hand starten. Sie führt die Tests aus, ruft die Dateien ab, bereinigt sie, erzeugt die Aggregate, committet die Daten und veröffentlicht die Seite auf GitHub Pages. Fehlt eine Datei, läuft der Rest weiter und die Action meldet eine Warnung.

Die Seite: https://j-wider.github.io/sellers-json-monitor/

## Stand und Grenzen

- Das Dashboard zeigt einen Monat. Die Tabelle „Veränderung zum Vormonat“ erscheint, sobald ein zweiter Monat vorliegt.
- Die Dateien enthalten Seller-IDs, keine Mengen. Die Zahlen beschreiben Einträge, nicht Umsatz oder Impressions.
- Das Dashboard ist standardmäßig dunkel, ein Schalter oben wechselt auf Hell.

## Lizenz

MIT, siehe `LICENSE`. D3 und d3-sankey in `site/vendor/` stehen unter ihren eigenen Lizenzen (ISC).
