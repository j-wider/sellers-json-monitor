# ads.txt-Abgleich und Vermarkter-Zuordnung

Stand: 13.11.2026. Konzept, freigegeben im Gespräch, noch nicht umgesetzt.

## Ziel

Das Dashboard zählt bisher Einträge in sellers.json-Dateien. Bei deutschen Angeboten steht dort oft nur der Vermarkter (z. B. iqdigital.de) und nicht die Website (z. B. handelsblatt.com). Im November-Snapshot gibt es nur 84 .de-Domains, viele davon Vermarkter-Domains.

Die Erweiterung geht den umgekehrten Weg: Sie startet bei einer Liste der in Deutschland meistgenutzten Websites, liest deren ads.txt und schlägt jede Zeile über SSP und Seller-ID in den vorhandenen sellers.json-Daten nach. So entsteht für jede Website die Zuordnung zu SSP und Vermarkter.

Zielgruppe ist die Branche, das Dashboard bleibt öffentlich. Wie bisher beschreibt es nur und bewertet nicht.

## Entscheidungen

- Startliste: Chrome-UX-Report (CrUX), Land Deutschland, Rangstufen bis 10.000. Andere Quellen wurden verworfen: Tranco filtert nur nach Endung und verliert deutsche .com/.net-Angebote, die AGOF ist als Quelle nicht mehr verlässlich, interne Listen aus dem Agenturgeschäft sind vertraulich.
- Bezug der CrUX-Daten ohne Google-Konto über das öffentliche Repository `zakird/crux-top-lists`, Datei `data/country/de/YYYYMM.csv.gz`. Ausweichweg bei Ausfall: eigene Abfrage über die BigQuery-Sandbox (kein Rechnungskonto nötig).
- Einbau in den bestehenden Monatslauf, kein zweiter Lauf.
- Alle Daten liegen im Repository. Speicherplatz wird erst Thema, wenn das Repository gegen 1 GB geht.
- Erwachsenenseiten werden beim Lauf entfernt. Im Dashboard steht nur ihre Anzahl.
- Eine eigene Ansicht „Bestätigungsquote je SSP“ gibt es nicht. Der Abgleich läuft trotzdem, weil die Vermarkter-Zuordnung auf ihm beruht.
- Optional: Eine private Domain-Liste in einer von Git ignorierten Datei kann lokal statt der CrUX-Liste verwendet werden. Sie wird nie committet.

## Datenfluss

Der Monatslauf bekommt drei Schritte zwischen `clean.py` und `aggregate.py`.

### 1. Startliste: `scripts/crux.py MONAT`

- Lädt die neueste verfügbare Deutschland-Datei. Am 1. eines Monats ist das in der Regel die Datei des Vorvormonats, weil Google um den zweiten Dienstag des Folgemonats veröffentlicht.
- Behält Origins mit Rangstufe bis 10.000.
- Verdichtet Origins auf die Hauptdomain (`www.spiegel.de`, `m.spiegel.de` → `spiegel.de`) mit der Public Suffix List, damit `example.co.uk` richtig erkannt wird. Pro Hauptdomain zählt die beste Rangstufe. Für Oktober 2026 ergibt das 8.666 Hauptdomains, vor Entfernung der Erwachsenenseiten.
- Entfernt Domains, die in der Kategorie „adult“ einer frei verfügbaren Kategorie-Liste stehen. Vorgesehen ist die UT1-Blacklist der Universität Toulouse. Bezugsquelle und Lizenz sind vor der Umsetzung zu prüfen.
- Ergebnis: `data/crux/YYYY-MM.csv` mit Domain, Rangstufe, CrUX-Monat und Zahl der entfernten Domains.

### 2. Abruf: `scripts/adstxt_fetch.py MONAT`

- Ruft `https://DOMAIN/ads.txt` ab. Bei Fehlschlag folgt ein zweiter Versuch über `www.DOMAIN`.
- 20 Abrufe gleichzeitig, 10 Sekunden Zeitlimit, User-Agent mit Verweis auf das Repository.
- Weiterleitungen nur in dem Rahmen, den die IAB-Spezifikation ads.txt 1.1 erlaubt. Die genaue Regel ist bei der Umsetzung gegen die Spezifikation zu prüfen.
- Status je Domain: `gefunden`, `keine_adstxt` (404 oder leer), `fehlerseite` (HTML statt Text), `blockiert` (401, 403, 429), `zeitueberschreitung`, `fehler`.
- Ergebnis: `data/raw/YYYY-MM/adstxt.jsonl.gz` (Rohtext je Domain) und `data/raw/YYYY-MM/adstxt_log.json` (Status, Endadresse, Größe, SHA-256).

### 3. Zerlegung: `scripts/adstxt_parse.py MONAT`

- Zerlegt jede Datenzeile in Werbesystem-Domain, Seller-ID, Beziehung (DIRECT/RESELLER) und optional die Zertifizierungs-ID. Kommentare, Leerzeilen, BOM und Groß-/Kleinschreibung werden berücksichtigt.
- Liest die Variablen `OWNERDOMAIN`, `MANAGERDOMAIN`, `CONTACT` und `SUBDOMAIN`.
- Erkennt die Platzhalter-Zeile, mit der ein Publisher erklärt, keine Werbung zu verkaufen.
- Ordnet Zeilen über das vorhandene Feld `adstxt_domain` in `config/ssps.json` einer der sechs SSPs zu.
- Einstufung je Domain: „Werbe-Website“, wenn mindestens eine gültige Zeile zu irgendeinem Werbesystem existiert; „keine Werbung“ bei fehlender ads.txt oder Platzhalter; „nicht abrufbar“ bei blockiert, Zeitüberschreitung oder Fehler.
- Ergebnis: `data/adstxt/YYYY-MM.csv.gz` mit einer Zeile je ads.txt-Zeile zu den sechs SSPs und eine Zusammenfassung je Domain (Zeilen gesamt, Reseller-Zeilen, Zahl der Werbesysteme, Variablen, Einstufung).

## Vermarkter-Logik

Jede ads.txt-Zeile zu einer der sechs SSPs wird über (SSP, Seller-ID) im sellers.json-Snapshot desselben Monats nachgeschlagen und einem Verkaufsweg zugeordnet:

| Verkaufsweg | Regel |
|---|---|
| selbst verkauft | sellers.json-Domain des Kontos = Website |
| über Vermarkter | Zeile ist DIRECT, Konto gehört laut sellers.json einer anderen Domain |
| über Reseller | Zeile ist RESELLER |
| über Google-Bidding | Konto ist Intermediary mit Domain google.com (Regel wie im bestehenden Dashboard) |
| unbekannt | Seller-ID steht in keiner sellers.json |

Vermarkter einer Website ist der Inhaber der DIRECT-Konten, sofern er nicht die Website selbst ist. `MANAGERDOMAIN` wird als zusätzliche Angabe gezeigt. Widersprechen sich beide, zeigt das Dashboard beide.

Vermarkter werden über ihre sellers.json-Domain gruppiert, nicht über den Namen, weil Namen je SSP unterschiedlich geschrieben sind. Häuser mit mehreren Domains (z. B. stroeer.de, stroeer.com, stroeerdigitalmedia.de) werden über die handgepflegte Datei `config/vermarkter.json` gebündelt:

```json
[
  {"id": "stroeer", "name": "Ströer", "domains": ["stroeer.de", "stroeer.com", "stroeerdigitalmedia.de"]}
]
```

Eine erste Fassung wird aus den Daten vorgeschlagen und von Jens geprüft. Später können hier Verlagsgruppen ergänzt werden.

## Dashboard

Drei neue Reiter neben den bestehenden Ansichten. Die bestehenden Ansichten bleiben unverändert. Die Daten liegen in einer eigenen Datei `data/aggregates/YYYY-MM-adstxt.json`, die erst beim Öffnen der Reiter geladen wird, damit die Startseite schnell bleibt.

### Vermarkter-Portfolio

- Übersichtstabelle: Vermarkter, Zahl der Websites, davon Top 1.000, SSPs, bei denen er auftritt.
- Detailansicht nach Klick: Sankey Vermarkter → SSPs und Liste der Websites mit Rangstufe.

### Website-Suche

- Suchfeld mit Vorschlägen über alle Domains der Startliste.
- Kopf: Rangstufe, Einstufung, Zeilen gesamt, Reseller-Zeilen, `MANAGERDOMAIN`/`OWNERDOMAIN`.
- Tabelle: SSP, Seller-ID, Verkäufer laut sellers.json, Verkaufsweg, DIRECT/RESELLER.
- Domains ohne Werbung oder nicht abrufbare Domains werden gefunden und mit ihrem Status angezeigt.

### Marktkennzahlen

- Kacheln: Anteil der Domains mit Werbung, mittlere Zeilenzahl der ads.txt, Anteil der Reseller-Zeilen.
- Je SSP: Zahl der Werbe-Websites, auf denen sie vorkommt, aufgeteilt nach Verkaufsweg.
- Alles nach Rangstufe (1.000, 5.000, 10.000) aufteilbar.
- Vergleich zum Vormonat, sobald zwei Monate vorliegen.

Jeder Reiter nennt den CrUX-Monat, das Abrufdatum, die Zahl nicht abrufbarer Domains und die Zahl entfernter Erwachsenenseiten.

## Fehlerbehandlung

- CrUX-Datei oder Kategorie-Liste nicht abrufbar: Der ads.txt-Teil wird für den Monat übersprungen, die Action meldet eine Warnung, der sellers.json-Teil läuft weiter. Ältere Listen werden nicht stillschweigend wiederverwendet.
- Mehr als 30 % der Domains nicht abrufbar: Warnung in der Action.
- Das Dashboard zeigt bei fehlenden ads.txt-Daten einen Hinweis statt leerer Reiter.

## Tests

Im Stil der bestehenden `unittest`-Tests, ohne Netzwerkzugriff:

- ads.txt-Zerlegung: Kommentare, Inline-Kommentare, Groß-/Kleinschreibung, BOM, Variablen, Platzhalter-Zeile, HTML-Fehlerseite, fehlerhafte Zeilen.
- Domain-Verdichtung: `www.`, `m.`, mehrteilige Endungen.
- Verkaufswege: kleines Beispiel mit Website, Vermarkter, Reseller, Google-Konto und unbekannter ID.
- Weiterleitungsregel: erlaubte und unerlaubte Fälle.

Die Tests laufen vor jedem Monatslauf. Schlägt einer fehl, startet der Lauf nicht.

## Grenzen

- CrUX misst Chrome-Nutzung. Seiten, die stark in anderen Browsern oder Apps genutzt werden, sind unterrepräsentiert.
- Die Rangstufen sind grob, es gibt keine genauen Plätze.
- ads.txt zeigt, wer verkaufen darf, nicht wie viel verkauft wird.
- Die Erkennung von Erwachsenenseiten über eine Kategorie-Liste ist nicht vollständig.
- Die Startliste hängt von einem fremden Repository ab.

## Spätere Ausbaustufen (nicht Teil dieses Konzepts)

Verlagsgruppen in `config/vermarkter.json`, OpenSincera (nach Prüfung der Nutzungsbedingungen), Rückblick über archivierte sellers.json-Dateien in der Wayback Machine.
