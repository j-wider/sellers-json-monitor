# ads.txt-Abgleich und Vermarkter-Zuordnung: Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Der Monatslauf liest die ads.txt der rund 8.700 meistgenutzten Websites in Deutschland, ordnet jede Zeile über SSP und Seller-ID den vorhandenen sellers.json-Daten zu und zeigt das Ergebnis in drei neuen Dashboard-Reitern.

**Aufbau:** Vier neue Skripte laufen zwischen `clean.py` und `aggregate.py` (Startliste, Abruf, Zerlegung, Aggregat). Reine Funktionen (Domain-Verdichtung, Zerlegung, Weiterleitungsregel, Verkaufswege) liegen getrennt vom Netzwerkcode und haben `unittest`-Tests ohne Netzwerk. Das Dashboard lädt die neue Datei `data/aggregates/YYYY-MM-adstxt.json` erst beim Öffnen eines neuen Reiters.

**Technik:** Python 3.12 nur mit Standardbibliothek (wie bisher, kein `pip install` in der Action), `unittest`, GitHub Actions, Dashboard in HTML/CSS/JS mit D3 und d3-sankey aus `site/vendor/`.

**Konzept:** `docs/superpowers/specs/2026-11-13-adstxt-vermarkter-design.md`

## Global Constraints

- Nur Standardbibliothek. Keine neuen Python-Pakete.
- Startliste: `https://raw.githubusercontent.com/zakird/crux-top-lists/main/data/country/de/YYYYMM.csv.gz`, Spalten `origin,rank`, Rangstufen bis einschließlich 10.000 (Werte 1000, 5000, 10000).
- Erwachsenen-Liste: UT1, Spiegel `olbat/ut1-blacklists`, Dateien `blacklists/adult/domains.0`, `domains.1`, `domains.2` (zusammen rund 124 MB, eine Domain je Zeile). Lizenz CC BY-SA 4.0, im Dashboard und README nennen.
- Abruf: 20 gleichzeitig, 10 Sekunden Zeitlimit, User-Agent `sellers-json-monitor/0.2 (+https://github.com/j-wider/sellers-json-monitor)`.
- Statuswerte Abruf: `gefunden`, `keine_adstxt`, `fehlerseite`, `blockiert`, `zeitueberschreitung`, `fehler`.
- Einstufung: `werbung`, `keine_werbung`, `nicht_abrufbar` (Anzeige: „Werbe-Website“, „keine Werbung“, „nicht abrufbar“).
- Verkaufswege: `selbst`, `vermarkter`, `reseller`, `google`, `unbekannt`.
- Google-Regel wie bisher: Typ `INTERMEDIARY` und `domain_clean == "google.com"`.
- Warnschwelle: mehr als 30 % der Domains `nicht_abrufbar`.
- Erwachsenenseiten werden beim Lauf entfernt, nur ihre Anzahl wird gespeichert.
- Bestehende Ansichten des Dashboards bleiben unverändert.
- Dashboard ohne cremefarbene Hintergründe, kursive Akzentwörter, nummerierte Abschnittslabels, Monospace-Labels und pillenförmige Buttons. Beim Bau der Reiter den taste-skill anwenden.
- Kommentare, Logausgaben und Texte auf Deutsch, Stil wie im bestehenden Code.
- Arbeit auf dem Branch `adstxt`. Kein Push ohne Rückfrage bei Jens.

## Geprüfte offene Punkte aus der Übergabe

- **Weiterleitungen (IAB ads.txt 1.1, GitHub `InteractiveAdvertisingBureau/Supply-Chain-Validation`, Datei `ads.txt v1.1.md`):** 301, 302 und 307 werden verfolgt, solange jedes Ziel innerhalb der ursprünglichen Hauptdomain bleibt (mehrere Sprünge erlaubt, z. B. http → https). Genau ein Sprung auf eine fremde Domain ist erlaubt. Leitet diese fremde Adresse weiter, ist das ein Fehler. Andere Weiterleitungen sind Fehler. Außerdem: 404 heißt „keine Erklärungen“; ein anderer Content-Type als `text/plain` gilt als Fehler.
- **UT1:** Lizenz CC BY-SA 4.0 laut README des GitHub-Spiegels, der täglich mit der Universität abgeglichen wird (letzter Commit 12.10.2026). Die Seite der Universität war beim Prüfen nicht erreichbar (HTTP 503). Die Liste enthält auch Phishing-Domains, die für unsere Startliste keine Rolle spielen.
- **`config/vermarkter.json`:** Task 7 erzeugt einen Vorschlag aus den Daten, Jens prüft ihn.

## Abweichungen vom Konzept (bewusst, zur Freigabe)

- Die Zahl der entfernten Erwachsenenseiten steht nicht als Spalte in `data/crux/YYYY-MM.csv`, sondern in `data/crux/YYYY-MM.meta.json` zusammen mit CrUX-Monat und Quell-URLs. Eine Spalte mit demselben Wert in jeder Zeile wäre doppelt.
- Die Zusammenfassung je Domain liegt in einer zweiten Datei `data/adstxt/YYYY-MM-domains.csv.gz` neben `data/adstxt/YYYY-MM.csv.gz`.
- Status `fehlerseite` (HTML statt Text) wird als „keine Werbung“ eingestuft, weil die Spezifikation diesen Content-Type als ungültig behandelt und der Server erreichbar war.
- Die Public Suffix List wird als `config/public_suffix_list.dat` ins Repository gelegt (MPL 2.0) und nicht bei jedem Lauf geladen. Ein Abruf weniger, der scheitern kann.

## Review Focus

1. ads.txt-Zeilen mit anderen Systemdomains derselben SSP (z. B. `equativ.com` statt `smartadserver.com`, `xandr.com` statt `appnexus.com`): Diese Zeilen sollen der richtigen SSP zugeordnet werden, nicht verloren gehen. Task 5 prüft die echten Daten und ergänzt `adstxt_aliases` in `config/ssps.json`.
2. Seller-ID, die in einer sellers.json doppelt vorkommt (Flag `id_doppelt`): Der Abgleich soll deterministisch den ersten Eintrag mit Typ `PUBLISHER` nehmen, sonst den ersten. Test in Task 6.
3. Vertrauliche Konten (`is_confidential`, ohne Domain) in DIRECT-Zeilen: Verkaufsweg `vermarkter` mit Vermarkter-Kennung `vertraulich`, damit sie gezählt, aber keinem Haus zugeschrieben werden. Test in Task 6.
4. Website mit `www.`-Weiterleitung auf eine andere Hauptdomain (z. B. `bild.de` → `www.bild.de` ist erlaubt, `example.de` → `cdn.fremd.net/ads.txt` → `andere.net` ist Fehler). Tests in Task 4.
5. ads.txt mit Windows-Zeilenenden, Tabulatoren statt Leerzeichen und Seller-IDs mit führenden Nullen oder Großbuchstaben: Seller-ID unverändert (nur getrimmt) vergleichen, Systemdomain klein. Tests in Task 3.

---

## Dateien

| Datei | Aufgabe |
|---|---|
| `config/public_suffix_list.dat` | Public Suffix List (neu, Task 1) |
| `scripts/domains.py` | Hauptdomain bestimmen (neu, Task 1) |
| `scripts/crux.py` | Startliste aus CrUX, Erwachsenenfilter (neu, Task 2) |
| `scripts/adstxt_fetch.py` | Abruf der ads.txt mit Weiterleitungsregel (neu, Task 4) |
| `scripts/adstxt_parse.py` | Zerlegung, SSP-Zuordnung, Einstufung (neu, Task 3 und 5) |
| `scripts/vermarkter.py` | Verkaufswege und Vermarkter je Website (neu, Task 6) |
| `scripts/vermarkter_vorschlag.py` | Vorschlag für `config/vermarkter.json` (neu, Task 7) |
| `config/vermarkter.json` | Bündelung von Vermarkter-Domains (neu, Task 7) |
| `scripts/aggregate_adstxt.py` | Datei fürs Dashboard (neu, Task 8) |
| `.github/workflows/monthly.yml` | Einbau in den Monatslauf (Task 9) |
| `site/index.html`, `site/style.css` | Reiterleiste und Bereiche (Task 10 bis 13) |
| `site/adstxt.js` | Logik der drei neuen Reiter (neu, Task 10 bis 13), damit `app.js` unverändert bleibt |
| `tests/test_domains.py`, `tests/test_crux.py`, `tests/test_adstxt_parse.py`, `tests/test_adstxt_fetch.py`, `tests/test_vermarkter.py`, `tests/test_aggregate_adstxt.py` | Tests (neu) |
| `README.md` | Doku (Task 14) |

Alle Skripte folgen dem Muster der bestehenden: `ROOT = Path(__file__).resolve().parent.parent`, `main(month)`, Aufruf `python scripts/X.py YYYY-MM`. Tests importieren wie `tests/test_clean.py` über `sys.path.insert(0, ... / "scripts")`.

---

### Task 1: Hauptdomain bestimmen

**Files:**
- Create: `config/public_suffix_list.dat`, `scripts/domains.py`, `tests/test_domains.py`

**Interfaces:**
- Produces: `load_psl(path: Path | None = None) -> dict` (Standardpfad `ROOT/config/public_suffix_list.dat`; Rückgabe `{"rules": set[str], "wild": set[str], "exc": set[str]}`), `registrable_domain(host: str, psl: dict) -> str` (leerer String, wenn `host` selbst eine Endung oder ungültig ist), `host_from_origin(origin: str) -> str` (entfernt Schema, Port, Pfad, Punkt am Ende, klein).

- [ ] **Step 1: Branch anlegen und Liste holen**

```powershell
git switch -c adstxt
python -c "import urllib.request; open('config/public_suffix_list.dat','wb').write(urllib.request.urlopen('https://publicsuffix.org/list/public_suffix_list.dat', timeout=60).read())"
```

Erwartet: Datei rund 230 KB, beginnt mit dem MPL-Kommentar.

- [ ] **Step 2: Tests schreiben**

```python
class RegistrableTests(unittest.TestCase):
    psl = load_psl()
    def test_www_und_m(self):
        for h in ("www.spiegel.de", "m.spiegel.de", "spiegel.de"):
            self.assertEqual(registrable_domain(h, self.psl), "spiegel.de")
    def test_mehrteilige_endung(self):
        self.assertEqual(registrable_domain("m.bbc.co.uk", self.psl), "bbc.co.uk")
        self.assertEqual(registrable_domain("shop.example.com.au", self.psl), "example.com.au")
    def test_private_endung(self):
        self.assertEqual(registrable_domain("foo.github.io", self.psl), "foo.github.io")
    def test_nur_endung(self):
        self.assertEqual(registrable_domain("co.uk", self.psl), "")
    def test_origin(self):
        self.assertEqual(host_from_origin("https://WWW.Spiegel.de:443/"), "www.spiegel.de")
        self.assertEqual(host_from_origin("http://example.de."), "example.de")
```

- [ ] **Step 3: Tests laufen lassen**, `python -m unittest tests.test_domains -v`. Erwartet: FAIL, `ModuleNotFoundError: domains`.
- [ ] **Step 4: `domains.py` umsetzen.** Algorithmus der PSL: längste passende Regel gewinnt, `*.`-Regeln über `wild`, `!`-Ausnahmen über `exc`; Hauptdomain ist die Endung plus ein Label. Kommentare (`//`) und Leerzeilen überspringen, ICANN- und private Abschnitte beide verwenden.
- [ ] **Step 5: Tests laufen lassen.** Erwartet: PASS, und `python -m unittest discover -s tests` bleibt grün.
- [ ] **Step 6: Commit** `Hauptdomain über Public Suffix List bestimmen`.

### Task 2: Startliste aus CrUX

**Files:**
- Create: `scripts/crux.py`, `tests/test_crux.py`
- Output: `data/crux/YYYY-MM.csv`, `data/crux/YYYY-MM.meta.json`

**Interfaces:**
- Consumes: `load_psl`, `registrable_domain`, `host_from_origin` (Task 1).
- Produces:
  - `crux_candidates(month: str) -> list[str]`: `"2026-12"` → `["202611", "202610", "202609"]` (Vormonat bis drei Monate zurück, neueste zuerst).
  - `compress_origins(rows: Iterable[tuple[str, int]], psl, max_rank: int = 10000) -> dict[str, int]`: Hauptdomain → beste (kleinste) Rangstufe.
  - `adult_hits(lines: Iterable[str], domains: set[str], psl) -> set[str]`: Domains der Startliste, deren Hauptdomain oder exakter Name in der Liste steht. Liest zeilenweise und behält nur Treffer, damit die 124 MB nicht als Menge im Speicher landen.
  - `main(month) -> int`: 0 bei Erfolg, 2 wenn CrUX-Datei oder UT1-Liste nicht abrufbar war (dann wird nichts geschrieben).
  - CSV-Spalten: `domain,rank,crux_month`, sortiert nach Rang, dann Domain.
  - Meta-JSON: `{"crux_month": "202610", "crux_url": ..., "origins": int, "domains_before_filter": int, "adult_removed": int, "adult_source": ..., "created_at": ISO}`.

- [ ] **Step 1: Tests schreiben**

```python
def test_kandidaten_jahreswechsel(self):
    self.assertEqual(crux_candidates("2027-01"), ["202612", "202611", "202610"])
def test_verdichtung_beste_rangstufe(self):
    rows = [("https://www.spiegel.de", 5000), ("https://m.spiegel.de", 1000),
            ("https://x.de", 50000), ("http://bbc.co.uk", 10000)]
    self.assertEqual(compress_origins(rows, PSL), {"spiegel.de": 1000, "bbc.co.uk": 10000})
def test_erwachsenenfilter(self):
    lines = ["foo.com\n", "sub.bar.de\n", "\n", "# x\n"]
    self.assertEqual(adult_hits(lines, {"foo.com", "bar.de", "spiegel.de"}, PSL), {"foo.com"})
```

`sub.bar.de` in der Liste sperrt `bar.de` nicht (nur der exakte Name oder die Hauptdomain des Listeneintrags, wenn dieser selbst eine Hauptdomain ist).

- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Umsetzen.** Abruf mit `urllib`, Timeout 120 s, User-Agent aus den Global Constraints. CrUX: Kandidaten der Reihe nach, erste mit HTTP 200 nehmen. UT1: die drei Teile nacheinander streamen (`io.TextIOWrapper` über die Antwort), Teile können mitten in einer Zeile getrennt sein, daher den Rest der letzten Zeile an den nächsten Teil hängen. Bei Fehler: Meldung `::warning::` auf stdout und Rückgabe 2.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Echter Lauf** `python scripts/crux.py 2026-11`. Erwartet: CrUX-Monat `202610`, etwa 8.666 Domains vor dem Filter (Wert aus dem Konzept), eine zweistellige oder kleine dreistellige Zahl entfernter Domains. Abweichungen notieren.
- [ ] **Step 6: Commit** inkl. `data/crux/2026-11.*`: `Startliste aus CrUX mit Erwachsenenfilter`.

### Task 3: ads.txt zerlegen

**Files:**
- Create: `scripts/adstxt_parse.py` (zunächst nur die Zerlegung), `tests/test_adstxt_parse.py`

**Interfaces:**
- Produces: `parse_adstxt(text: str) -> dict` mit
  `{"records": [{"system": str, "seller_id": str, "relation": "DIRECT"|"RESELLER", "cert": str}], "variables": {"OWNERDOMAIN": [..], "MANAGERDOMAIN": [..], "CONTACT": [..], "SUBDOMAIN": [..]}, "placeholder": bool, "invalid": int}`.
  Systemdomain klein und getrimmt, Seller-ID nur getrimmt, Beziehung groß. Variablennamen ohne Rücksicht auf Groß-/Kleinschreibung. Platzhalter laut Spezifikation 1.1: Zeile `placeholder.example.com, placeholder, DIRECT, placeholder`.

- [ ] **Step 1: Tests schreiben** (ein Test je Fall):
  - Kommentarzeile und Inline-Kommentar: `"# x\ngoogle.com, pub-1, DIRECT, f08c47fec0942fa0 # gut\n"` → ein Datensatz mit `cert == "f08c47fec0942fa0"`.
  - BOM und `\r\n`: `"﻿PubMatic.com, 156, reseller\r\n"` → `system == "pubmatic.com"`, `relation == "RESELLER"`.
  - Tabulatoren: `"appnexus.com,\t0123,\tDIRECT"` → `seller_id == "0123"`.
  - Variablen: `"OwnerDomain=spiegel.de\nMANAGERDOMAIN=iqdigital.de\ncontact=a@b.de"` → Listen gefüllt, keine Datensätze.
  - Platzhalter → `placeholder is True`, `records == []`.
  - Fehlerhafte Zeilen (`"nur.eins"`, `"a.com, 1, INDIRECT"`, `"a.com, , DIRECT"`) → `invalid == 3`.
  - HTML-Text (`"<!doctype html><html>..."`) → `records == []`, `invalid >= 1`.
- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: `parse_adstxt` umsetzen.**
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit** `ads.txt-Zeilen zerlegen`.

### Task 4: ads.txt abrufen

**Files:**
- Create: `scripts/adstxt_fetch.py`, `tests/test_adstxt_fetch.py`
- Output: `data/raw/YYYY-MM/adstxt.jsonl.gz` (je gefundener Domain eine Zeile `{"domain": ..., "text": ...}`), `data/raw/YYYY-MM/adstxt_log.json`

**Interfaces:**
- Consumes: `registrable_domain`, `load_psl` (Task 1); `data/crux/YYYY-MM.csv` (Task 2).
- Produces:
  - `redirect_allowed(domain: str, chain: list[str], psl) -> bool`: `chain` sind die bisher besuchten URLs inkl. der neuen. Regel aus „Geprüfte offene Punkte“.
  - `classify_response(http_status: int | None, content_type: str, body: bytes, error: str | None) -> str`: Statuswert aus den Global Constraints. 404 oder leerer Text → `keine_adstxt`; 401/403/429 → `blockiert`; Content-Type `text/html` oder Text beginnt mit `<` → `fehlerseite`; `error == "timeout"` → `zeitueberschreitung`; anderer Fehler oder anderer Status → `fehler`; 200 mit Text → `gefunden`. Fehlender Content-Type bei sonst gültigem Text gilt als `gefunden` (in der Praxis häufig).
  - `fetch_domain(domain: str, psl) -> tuple[dict, str | None]`: Logeintrag `{"domain", "status", "url", "final_url", "http_status", "bytes", "sha256", "redirects", "detail"}` und Text oder `None`. Zuerst `https://DOMAIN/ads.txt`, bei anderem Status als `gefunden` oder `keine_adstxt` zweiter Versuch mit `https://www.DOMAIN/ads.txt`.
  - `main(month, limit: int | None = None) -> int`: Kommandozeile `python scripts/adstxt_fetch.py 2026-11 [--limit N]`. Rückgabe 0; gibt `::warning::` aus, wenn mehr als 30 % `blockiert`, `zeitueberschreitung` oder `fehler` sind.

- [ ] **Step 1: Tests schreiben**

```python
def test_weiterleitung_gleiche_hauptdomain(self):
    self.assertTrue(redirect_allowed("bild.de", ["http://bild.de/ads.txt", "https://www.bild.de/ads.txt"], PSL))
def test_ein_sprung_fremd(self):
    self.assertTrue(redirect_allowed("a.de", ["https://a.de/ads.txt", "https://cdn.fremd.net/a/ads.txt"], PSL))
def test_zweiter_sprung_nach_fremd(self):
    self.assertFalse(redirect_allowed("a.de", ["https://a.de/ads.txt", "https://fremd.net/ads.txt", "https://www.fremd.net/ads.txt"], PSL))
def test_status(self):
    self.assertEqual(classify_response(404, "text/html", b"", None), "keine_adstxt")
    self.assertEqual(classify_response(200, "text/plain", b"  \n", None), "keine_adstxt")
    self.assertEqual(classify_response(200, "text/html; charset=utf-8", b"<html>", None), "fehlerseite")
    self.assertEqual(classify_response(403, "", b"", None), "blockiert")
    self.assertEqual(classify_response(None, "", b"", "timeout"), "zeitueberschreitung")
    self.assertEqual(classify_response(200, "text/plain", b"a.com, 1, DIRECT", None), "gefunden")
```

- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Umsetzen.** Weiterleitungen von Hand verfolgen (eigener `HTTPRedirectHandler`, der `None` zurückgibt, dann `Location` lesen), höchstens 5 Sprünge, nur 301/302/307 (308 ebenfalls, weil gleichbedeutend mit 301; im Kommentar vermerken). Lesen auf 2 MB begrenzen. `concurrent.futures.ThreadPoolExecutor(max_workers=20)`, Ergebnisse nach Domain sortiert schreiben. SHA-256 über die Rohbytes.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Probelauf** `python scripts/adstxt_fetch.py 2026-11 --limit 50`. Erwartet: Log mit 50 Einträgen, die Mehrheit `gefunden`. Bekannte Seiten von Hand vergleichen (z. B. `spiegel.de/ads.txt` im Browser). Die Probedateien danach löschen, sie werden im Gesamtlauf (Task 14) neu erzeugt.
- [ ] **Step 6: Commit** `ads.txt abrufen mit Weiterleitungsregel der IAB`.

### Task 5: Zerlegung je Monat, SSP-Zuordnung, Einstufung

**Files:**
- Modify: `scripts/adstxt_parse.py`, `tests/test_adstxt_parse.py`, `config/ssps.json`
- Output: `data/adstxt/YYYY-MM.csv.gz`, `data/adstxt/YYYY-MM-domains.csv.gz`

**Interfaces:**
- Consumes: `parse_adstxt` (Task 3), Log und Rohtext aus Task 4, `data/crux/YYYY-MM.csv`.
- Produces:
  - `ssp_lookup(ssps: list[dict]) -> dict[str, str]`: Systemdomain → SSP-ID aus `adstxt_domain` und optionalem Feld `adstxt_aliases` (Liste).
  - `classify_site(status: str, parsed: dict | None) -> str`: `werbung` bei mindestens einem Datensatz (beliebiges System); `keine_werbung` bei `keine_adstxt`, `fehlerseite`, Platzhalter oder Datei ohne gültige Zeile; sonst `nicht_abrufbar`.
  - Zeilendatei, Spalten: `domain,ssp,seller_id,relation,cert` (nur Zeilen zu den sechs SSPs).
  - Domaindatei, Spalten: `domain,rank,status,einstufung,lines_total,reseller_lines,systems,invalid,ownerdomain,managerdomain,contact,subdomain` (Variablen mit `|` verbunden). Enthält alle Domains der Startliste, auch nicht abrufbare.

- [ ] **Step 1: Tests schreiben** für `ssp_lookup` (Alias wird erkannt) und `classify_site` (je ein Fall pro Einstufung, `fehlerseite` → `keine_werbung`, Datei nur mit Kommentaren → `keine_werbung`).
- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Umsetzen** inkl. `main(month)`.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Aliase prüfen.** Probelauf mit `--limit 300` in Task 4, dann `main`, und die häufigsten Systemdomains ausgeben, die keiner SSP zugeordnet sind. Domains, die sicher zu einer der sechs SSPs gehören (Kandidaten: `equativ.com`, `xandr.com`, `magnite.com`), als `adstxt_aliases` in `config/ssps.json` ergänzen. Nur aufnehmen, was die SSP selbst als ads.txt-Domain angibt; im Zweifel Jens fragen. Probedateien wieder löschen.
- [ ] **Step 6: Commit** `ads.txt je Monat zerlegen und SSPs zuordnen`.

### Task 6: Verkaufswege und Vermarkter

**Files:**
- Create: `scripts/vermarkter.py`, `tests/test_vermarkter.py`

**Interfaces:**
- Consumes: Snapshot-Zeilen (`iter_snapshot` aus `scripts/aggregate.py`), `registrable_domain` (Task 1).
- Produces:
  - `account_index(rows: Iterable[dict]) -> dict[tuple[str, str], dict]`: `(ssp, seller_id)` → `{"domain": str, "type": str, "name": str, "confidential": bool}`. Bei doppelter ID gewinnt der erste Eintrag mit Typ `PUBLISHER`, sonst der erste.
  - `sales_path(website: str, relation: str, account: dict | None, psl) -> str`. Reihenfolge der Prüfung: kein Konto → `unbekannt`; Google-Regel → `google`; Hauptdomain des Kontos = Website → `selbst`; `RESELLER` → `reseller`; sonst `vermarkter`.
  - `owner_key(account: dict, groups: dict[str, str], psl) -> str`: Hauptdomain des Kontos, über `groups` (Domain → Gruppen-ID aus `config/vermarkter.json`) auf die Gruppe abgebildet; vertraulich ohne Domain → `"vertraulich"`.
  - `load_groups(path: Path | None = None) -> tuple[dict[str, str], dict[str, str]]`: (Domain → ID, ID → Anzeigename). Fehlt die Datei, zwei leere dicts.
  - `site_vermarkter(website: str, lines: list[dict], index, groups, psl) -> list[str]`: sortierte Liste der Besitzer aller Zeilen mit Verkaufsweg `vermarkter`.

- [ ] **Step 1: Tests schreiben** mit einem kleinen Beispiel: Website `zeitung.de`; Konten `(pubmatic, "1")` Domain `zeitung.de` PUBLISHER, `(pubmatic, "2")` Domain `vermarkt.de` PUBLISHER, `(openx, "3")` Domain `stroeer.com`, `(openx, "4")` `google.com` INTERMEDIARY, `(magnite, "5")` vertraulich ohne Domain; Gruppe `stroeer` mit `stroeer.de`, `stroeer.com`.
  - Zeile `pubmatic 1 DIRECT` → `selbst`; `pubmatic 2 DIRECT` → `vermarkter`; `pubmatic 2 RESELLER` → `reseller`; `openx 4 RESELLER` → `google`; `index-exchange 9 DIRECT` → `unbekannt`.
  - `owner_key` für `stroeer.com` → `"stroeer"`, für das vertrauliche Konto → `"vertraulich"`.
  - `site_vermarkter` → `["stroeer", "vermarkt.de", "vertraulich"]` bei DIRECT-Zeilen zu 2, 3, 5.
  - Doppelte ID: zwei Einträge `(pubmatic, "7")`, erst INTERMEDIARY `a.de`, dann PUBLISHER `b.de` → Index liefert `b.de`.
- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Umsetzen.**
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit** `Verkaufswege und Vermarkter je Website bestimmen`.

### Task 7: Vorschlag für `config/vermarkter.json` (Haltepunkt für Jens)

**Files:**
- Create: `scripts/vermarkter_vorschlag.py`, `config/vermarkter.json`

**Interfaces:**
- Consumes: Task 5 und 6.
- Produces: `config/vermarkter.json` im Format des Konzepts (`[{"id", "name", "domains"}]`).

- [ ] **Step 1: Daten für November erzeugen.** Volle Läufe `crux.py`, `adstxt_fetch.py`, `adstxt_parse.py` für `2026-11` (Abruf dauert geschätzt 10 bis 30 Minuten, im Hintergrund starten).
- [ ] **Step 2: Skript schreiben**, das alle Besitzer-Domains mit Verkaufsweg `vermarkter` zählt (Zahl der Websites, Namen laut sellers.json je SSP) und Domains mit ähnlichem Namen zu Gruppen-Vorschlägen zusammenfasst (gleicher erster Namensbestandteil, z. B. „Ströer“, „Stroeer SSP“). Ausgabe als Entwurf `config/vermarkter.json` und als lesbare Tabelle auf der Konsole.
- [ ] **Step 3: Jens prüfen lassen.** Tabelle der 30 größten Vermarkter mit vorgeschlagenen Gruppen zeigen und auf Freigabe oder Korrekturen warten. Kein Weiterarbeiten an Task 8 vor der Antwort; Task 9 und 10 dürfen parallel laufen.
- [ ] **Step 4: Commit** nach Freigabe: `Vermarkter-Gruppen, von Jens geprüft`.

### Task 8: Aggregat fürs Dashboard

**Files:**
- Create: `scripts/aggregate_adstxt.py`, `tests/test_aggregate_adstxt.py`
- Output: `data/aggregates/YYYY-MM-adstxt.json`

**Interfaces:**
- Consumes: Task 2 (Meta), Task 4 (Log), Task 5 (beide CSVs), Task 6 (alle Funktionen), `iter_snapshot` und `previous_month` aus `scripts/aggregate.py`.
- Produces: `build_adstxt(month, crux_meta, fetch_log, domains_rows, line_rows, index, groups, names, psl, prev: dict | None) -> dict` mit
  ```
  {"month", "crux_month", "fetched_at", "counts": {"domains", "werbung", "keine_werbung", "nicht_abrufbar", "adult_removed"},
   "sites": [{"d", "r", "e", "n", "res", "own", "mgr", "v": [owner], "rows": [[ssp, seller_id, seller_name, path, relation]]}],
   "vermarkter": [{"id", "name", "domains", "sites", "top1000", "ssps": {ssp: n_sites}, "site_list": [[d, r]]}],
   "market": {"1000"|"5000"|"10000": {"share_ads", "median_lines", "reseller_share", "per_ssp": {ssp: {path: n_sites}}}},
   "prev": market des Vormonats oder null}
  ```
  `sites` enthält alle Domains der Startliste, `rows` nur bei `werbung`. Rangstufen kumulativ (Stufe 5.000 enthält 1.000). `main(month)` schreibt die Datei kompakt (`separators=(",", ":")`) und überspringt mit Hinweis, wenn `data/crux/YYYY-MM.csv` fehlt. `index.json` bleibt unverändert (das Muster `????-??.json` trifft die neue Datei nicht).

- [ ] **Step 1: Tests schreiben** mit dem Beispiel aus Task 6 plus einer Domain `keine_werbung` und einer `nicht_abrufbar`: `counts` stimmt, Vermarkter `stroeer` hat `sites == 1`, `market["10000"]["per_ssp"]["pubmatic"]` zählt Websites (nicht Zeilen), `prev is None` ohne Vormonat.
- [ ] **Step 2: Tests laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Umsetzen.**
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Lauf für 2026-11 und Größe prüfen.** Ziel unter 5 MB. Ist die Datei größer, `rows` in eine zweite Datei `YYYY-MM-adstxt-sites.json` auslagern, die erst die Website-Suche lädt, und das hier im Plan vermerken.
- [ ] **Step 6: Commit** `Aggregat für ads.txt-Reiter`.

### Task 9: Einbau in den Monatslauf

**Files:**
- Modify: `.github/workflows/monthly.yml`

- [ ] **Step 1: Schritt „ads.txt“ zwischen „Abruf, Bereinigung, Aggregate“ und „Daten committen“ einfügen**, Reihenfolge innerhalb des bestehenden Schritts beibehalten (`clean.py` vor dem ads.txt-Teil, `aggregate.py` bleibt):

```yaml
      - name: ads.txt
        run: |
          MONTH=$(date -u +%Y-%m)
          if python scripts/crux.py "$MONTH"; then
            python scripts/adstxt_fetch.py "$MONTH"
            python scripts/adstxt_parse.py "$MONTH"
            python scripts/aggregate_adstxt.py "$MONTH"
          else
            echo "::warning::ads.txt-Teil für $MONTH übersprungen (Startliste oder Erwachsenenliste nicht abrufbar)."
          fi
```

  `timeout-minutes: 180` am Job setzen. Der Schritt „Seite zusammenstellen“ kopiert `data/aggregates` bereits vollständig, dort ist nichts zu tun.
- [ ] **Step 2: Prüfen.** Die vier Befehle des neuen Schritts lokal in derselben Reihenfolge ausführen (mit `--limit 50` beim Abruf) und Einrückung der YAML-Datei mit den bestehenden Schritten vergleichen. Ein echter Test der Action geht erst nach dem Push (Task 14).
- [ ] **Step 3: Commit** `ads.txt-Teil in den Monatslauf aufnehmen`.

### Task 10: Reiterleiste und Nachladen

**Files:**
- Modify: `site/index.html`, `site/style.css`
- Create: `site/adstxt.js`

**Interfaces:**
- Consumes: `data/aggregates/YYYY-MM-adstxt.json`; aktueller Monat aus `#month`.
- Produces: `window.adstxt = { show(tab: "vermarkter"|"suche"|"markt") }`; Laden einmal je Monat, Ergebnis im Speicher. Fehlt die Datei (404), zeigt jeder Reiter den Hinweis „Für diesen Monat liegen keine ads.txt-Daten vor.“ Jeder Reiter hat einen Kopf mit CrUX-Monat, Abrufdatum, Zahl nicht abrufbarer Domains und Zahl entfernter Erwachsenenseiten sowie dem Quellenhinweis zu CrUX und UT1 (CC BY-SA 4.0).

- [ ] **Step 1: Reiterleiste** unter dem Kopf: „Übersicht“ (bisheriger Inhalt von `<main>` unverändert in einem Bereich), „Vermarkter“, „Website-Suche“, „Marktkennzahlen“. Umschalten über `location.hash` (`#vermarkter`, `#suche`, `#markt`), damit Links teilbar sind. Tastaturbedienung nach ARIA-Muster „Tabs“. taste-skill anwenden; Stil an `style.css` (dunkel/hell) anpassen.
- [ ] **Step 2: Prüfen** mit `python -m http.server 8765` und dem Browserbereich: Übersicht sieht aus wie vorher (Screenshot vorher/nachher), Reiter wechseln, Hash bleibt beim Neuladen erhalten, Hinweis erscheint für 2026-10 (keine Daten). Konsole ohne Fehler, Breite 375 px ohne seitliches Scrollen.
- [ ] **Step 3: Commit** `Reiterleiste für ads.txt-Ansichten`.

### Task 11: Reiter „Vermarkter“

**Files:** Modify `site/adstxt.js`, `site/style.css`

- [ ] **Step 1: Übersichtstabelle** aus `vermarkter`: Vermarkter, Websites, davon Top 1.000, SSPs (Kürzel und Farbe aus `ssps` des Hauptaggregats). Sortierbar nach Spalte, Standard „Websites“ absteigend. Zeile `vertraulich` am Ende mit Erklärung.
- [ ] **Step 2: Detail nach Klick**: Sankey Vermarkter → SSPs (Strichstärke = Websites), darunter Liste der Websites mit Rangstufe. Sankey-Code aus `app.js` nicht kopieren, nur das gleiche `d3.sankey` nutzen.
- [ ] **Step 3: Prüfen** im Browser mit den Daten aus Task 8: Summen in der Tabelle mit einer Stichprobe aus `data/adstxt/2026-11.csv.gz` vergleichen (ein Vermarkter, von Hand gezählt).
- [ ] **Step 4: Commit** `Reiter Vermarkter-Portfolio`.

### Task 12: Reiter „Website-Suche“

**Files:** Modify `site/adstxt.js`, `site/style.css`

- [ ] **Step 1: Suchfeld** mit Vorschlägen (`<datalist>` oder eigene Liste, höchstens 20 Vorschläge, Treffer am Wortanfang zuerst). Eingabe wird mit `host_from_origin`-gleicher Logik in JS normalisiert (klein, ohne Schema und `www.`).
- [ ] **Step 2: Ergebnis**: Kopf mit Rangstufe, Einstufung, Zeilen gesamt, Reseller-Zeilen, `MANAGERDOMAIN`/`OWNERDOMAIN`; bei Widerspruch zwischen `MANAGERDOMAIN` und Vermarkter aus den Daten beide anzeigen. Tabelle SSP, Seller-ID, Verkäufer laut sellers.json, Verkaufsweg, DIRECT/RESELLER. Domains ohne Werbung oder nicht abrufbar zeigen ihren Status statt der Tabelle. Unbekannte Domain: „Nicht in der Startliste.“
- [ ] **Step 3: Prüfen** mit drei Domains: eine Werbe-Website mit Vermarkter, eine ohne ads.txt, eine nicht abrufbare (aus dem Log ausgesucht).
- [ ] **Step 4: Commit** `Reiter Website-Suche`.

### Task 13: Reiter „Marktkennzahlen“

**Files:** Modify `site/adstxt.js`, `site/style.css`

- [ ] **Step 1: Kacheln**: Anteil Domains mit Werbung, mittlere Zeilenzahl (Median), Anteil Reseller-Zeilen. Umschalter Rangstufe 1.000 / 5.000 / 10.000 (Standard 10.000).
- [ ] **Step 2: Je SSP** gestapelter Balken: Zahl der Werbe-Websites nach Verkaufsweg. dataviz-Skill für Farben der Verkaufswege anwenden; SSP-Farben bleiben wie im Hauptaggregat.
- [ ] **Step 3: Vormonat**: Ist `prev` gesetzt, Veränderung an den Kacheln anzeigen, sonst nichts.
- [ ] **Step 4: Prüfen** im Browser: Kachelwerte mit `market` aus der JSON-Datei vergleichen, Umschalter ändert alle Werte.
- [ ] **Step 5: Commit** `Reiter Marktkennzahlen`.

### Task 14: Gesamtlauf, Doku, Abschluss

**Files:** Modify `README.md`; Daten für `2026-11`

- [ ] **Step 1: Alle Tests** `python -m unittest discover -s tests -v`. Erwartet: alle grün.
- [ ] **Step 2: Gesamtlauf** für `2026-11` in der Reihenfolge der Action (ohne `fetch.py`, die sellers.json-Daten liegen vor). Erwartet: Anteil `nicht_abrufbar` unter 30 %, keine Warnung.
- [ ] **Step 3: README** ergänzen: neue Skripte im Abschnitt „Ablauf“, neue Ordner in „Was wo liegt“, Zählweise der Verkaufswege und Einstufung, Grenzen aus dem Konzept, Quellen (CrUX über `zakird/crux-top-lists`, UT1 mit CC BY-SA 4.0, Public Suffix List mit MPL 2.0). ki-stil-vermeiden anwenden.
- [ ] **Step 4: Größe des Repositorys** prüfen (`git count-objects -vH`) und Jens nennen.
- [ ] **Step 5: Commit** `README und Daten für 2026-11 mit ads.txt`.
- [ ] **Step 6: Jens fragen**, ob der Branch nach `main` und dann nach GitHub soll. Danach Action einmal von Hand starten lassen und das Ergebnis auf der Seite prüfen.

### Task 15 (optional, nur auf Wunsch): Private Domain-Liste

**Files:** Modify `scripts/crux.py`, `scripts/adstxt_fetch.py`, `scripts/adstxt_parse.py`, `scripts/aggregate_adstxt.py`, `.gitignore`

- [ ] Schalter `--privat`: Startliste aus `privat/domains.txt` (eine Domain je Zeile) statt CrUX, alle Ausgaben unter `privat/data/...` statt `data/...`. `privat/` in `.gitignore`. Test: mit `--privat` entsteht keine Datei unter `data/`, und `git status` zeigt nichts Neues. Dashboard lokal mit `?privat` auf `privat/data/aggregates` zeigen lassen.
