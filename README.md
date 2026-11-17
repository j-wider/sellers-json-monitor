# sellers.json Monitor

Ruft die öffentlichen sellers.json-Dateien von sechs SSPs ab (PubMatic, Magnite, Index Exchange, OpenX, Equativ, Microsoft Monetize), bereinigt die Einträge und zeigt Rollenverhältnis, Überschneidung direkt gelisteter Publisher und eine Sonderauswertung für .de-Domains in einem Dashboard. Die Auswertung beschreibt nur, sie bewertet nichts.

Dazu kommt ein Abgleich von der Website-Seite her: Für die rund 8.000 in Deutschland meistgenutzten Websites werden die ads.txt-Dateien gelesen und jede Zeile über SSP und Seller-ID in den sellers.json-Daten nachgeschlagen. Daraus entstehen die Reiter „Vermarkter“, „Website-Suche“ und „Marktkennzahlen“. Konzept: `docs/superpowers/specs/2026-11-13-adstxt-vermarkter-design.md`.

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

ads.txt-Teil (braucht den Snapshot aus `clean.py`):

```bash
python scripts/crux.py 2026-11
python scripts/adstxt_fetch.py 2026-11
python scripts/adstxt_parse.py 2026-11
python scripts/aggregate_adstxt.py 2026-11
```

`crux.py` holt die Startliste und entfernt Erwachsenenseiten. `adstxt_fetch.py` ruft die ads.txt ab (20 gleichzeitig, 10 Sekunden Zeitlimit, dauert rund 10 Minuten; `--limit 50` für einen Probelauf). `adstxt_parse.py` zerlegt die Dateien, `aggregate_adstxt.py` erzeugt die Daten fürs Dashboard. Einen Vorschlag für `config/vermarkter.json` erzeugt `python scripts/vermarkter_vorschlag.py 2026-11` (mit `--schreiben` wird die Datei überschrieben).

Dashboard starten und im Browser öffnen:

```bash
python -m http.server 8765
```

Dann `http://localhost:8765/site/` aufrufen.

Tests (ohne Netzwerkzugriff):

```bash
python -m unittest discover -s tests -v
```

## Was wo liegt

| Ordner | Inhalt |
|---|---|
| `config/ssps.json` | Liste der SSPs mit URL, Farbe, Kürzel und ads.txt-Domain (`adstxt_domain`, dazu `adstxt_aliases`). Ein weiterer Eintrag nimmt eine weitere SSP auf. |
| `config/vermarkter.json` | Von Hand geprüfte Bündelung von Vermarkter-Domains zu Häusern. |
| `config/public_suffix_list.dat` | Public Suffix List (MPL 2.0), um `www.spiegel.de` auf `spiegel.de` zu verdichten. |
| `data/raw/YYYY-MM/` | Rohdateien (gzip) und `fetch_log.json` mit Abrufzeit, Größe und SHA-256. Dazu `adstxt.jsonl.gz` (Rohtext je gefundener ads.txt) und `adstxt_log.json` (Status, Endadresse, Größe, SHA-256 je Domain). |
| `data/snapshots/YYYY-MM.csv.gz` | Eine Zeile pro Seller (gzip), Originalwerte (`domain_raw`) und bereinigte Werte nebeneinander. |
| `data/crux/YYYY-MM.csv` | Startliste: Domain, Rangstufe, CrUX-Monat. `YYYY-MM.meta.json` nennt Quelle und Zahl der entfernten Erwachsenenseiten. |
| `data/adstxt/YYYY-MM.csv.gz` | Eine Zeile je ads.txt-Zeile zu einer der sechs SSPs. `YYYY-MM-domains.csv.gz` fasst jede Domain zusammen (Status, Einstufung, Zeilen, Variablen). |
| `data/aggregates/YYYY-MM.json` | Zähltabellen und Auswertungen, die das Dashboard lädt. |
| `data/aggregates/YYYY-MM-adstxt.json` | Daten der ads.txt-Reiter. Die einzelnen Zeilen je Website liegen in `YYYY-MM-adstxt/` nach Anfangsbuchstabe der Domain. |
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

## ads.txt-Abgleich

Startliste ist der Chrome-UX-Report (CrUX) für Deutschland, alle Origins bis Rangstufe 10.000, bezogen über [zakird/crux-top-lists](https://github.com/zakird/crux-top-lists). Google veröffentlicht um den zweiten Dienstag des Folgemonats, am 1. eines Monats ist die neueste Datei meist die des Vorvormonats. Origins werden auf die Hauptdomain verdichtet, es zählt die beste Rangstufe. Erwachsenenseiten werden mit der Kategorie „adult“ der UT1-Liste der Universität Toulouse Capitole entfernt (CC BY-SA 4.0, Spiegel [olbat/ut1-blacklists](https://github.com/olbat/ut1-blacklists)).

Abruf von `https://DOMAIN/ads.txt`, bei Misserfolg von `https://www.DOMAIN/ads.txt`. Weiterleitungen nach IAB ads.txt 1.1: innerhalb der Hauptdomain beliebig viele, dazu höchstens ein Sprung auf eine fremde Domain, die selbst nicht weiterleiten darf. Status je Domain: `gefunden`, `keine_adstxt` (404, 410 oder leer), `fehlerseite` (HTML statt Text), `blockiert` (401, 403, 429), `zeitueberschreitung`, `fehler`.

Einstufung: „Werbe-Website“ mit mindestens einer gültigen Zeile zu irgendeinem Werbesystem. „Keine Werbung“ ohne ads.txt, mit HTML-Seite statt ads.txt, mit der Platzhalter-Zeile der Spezifikation oder ohne gültige Zeile. „Nicht abrufbar“ bei `blockiert`, `zeitueberschreitung` oder `fehler`.

Verkaufsweg je Zeile, nachgeschlagen über (SSP, Seller-ID) im sellers.json-Snapshot desselben Monats und in dieser Reihenfolge geprüft:

| Verkaufsweg | Regel |
|---|---|
| Seller-ID unbekannt | Die Seller-ID steht in keiner sellers.json. |
| über Google-Bidding | Konto mit Typ Intermediary und Domain `google.com`. |
| selbst verkauft | Die Hauptdomain des Kontos ist die Website. |
| über Reseller | Die Zeile ist RESELLER. |
| über Vermarkter | Die Zeile ist DIRECT, das Konto gehört einer anderen Domain. |

Vermarkter einer Website sind die Inhaber dieser DIRECT-Konten, gruppiert nach ihrer sellers.json-Domain und über `config/vermarkter.json` zu Häusern gebündelt. Konten ohne Domain (vertraulich) stehen gesammelt unter „Vertraulich“. Steht eine Seller-ID mehrfach in einer sellers.json, zählt der erste Eintrag mit Typ Publisher. `equativ.com` und `xandr.com` gelten als ads.txt-Domains von Equativ und Microsoft Monetize, weil ihre Seller-IDs in deren sellers.json stehen. SpotX und Telaria (heute Magnite) haben eigene ID-Räume und werden nicht zugeordnet.

In den Marktkennzahlen zählt eine Website je SSP einmal, beim direktesten Weg (selbst vor Vermarkter, Reseller, Google-Bidding, unbekannt). Der Anteil der Websites mit Werbung bezieht sich auf die abrufbaren Websites.

Grenzen: CrUX misst Chrome-Nutzung, Seiten mit viel App- oder Fremdbrowser-Nutzung fehlen eher. Die Rangstufen sind grob. ads.txt zeigt, wer verkaufen darf, nicht wie viel verkauft wird. Die Kategorie-Liste erkennt nicht jede Erwachsenenseite und enthält einzelne Grenzfälle. Die Startliste hängt von einem fremden Repository ab.

## Automatischer Monatslauf

Die GitHub Action `Monatslauf` läuft am 1. jedes Monats um 06:00 UTC und lässt sich unter „Actions“ von Hand starten. Sie führt die Tests aus, ruft die Dateien ab, bereinigt sie, erzeugt die Aggregate, führt den ads.txt-Teil aus, committet die Daten und veröffentlicht die Seite auf GitHub Pages. Fehlt eine Datei, läuft der Rest weiter und die Action meldet eine Warnung. Sind Startliste oder Erwachsenen-Liste nicht abrufbar, wird der ads.txt-Teil für den Monat übersprungen; ältere Listen werden nicht wiederverwendet. Sind mehr als 30 % der Websites nicht abrufbar, meldet die Action ebenfalls eine Warnung.

Die Seite: https://j-wider.github.io/sellers-json-monitor/

## Stand und Grenzen

- Das Dashboard zeigt einen Monat. Die Tabelle „Veränderung zum Vormonat“ erscheint, sobald ein zweiter Monat vorliegt.
- Die Dateien enthalten Seller-IDs, keine Mengen. Die Zahlen beschreiben Einträge, nicht Umsatz oder Impressions.
- Das Dashboard ist standardmäßig dunkel, ein Schalter oben wechselt auf Hell.

## Lizenz

MIT, siehe `LICENSE`. D3 und d3-sankey in `site/vendor/` stehen unter ihren eigenen Lizenzen (ISC). Die Public Suffix List steht unter der MPL 2.0, die UT1-Liste unter CC BY-SA 4.0.
