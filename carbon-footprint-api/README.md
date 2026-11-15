# Carbon-Footprint-API

REST-Schnittstelle des DPPviewer. Stellt Asset Administration Shells aus AAS- und AASX-Dateien (Ordner `../repo`)
unter `/api/v4` bereit und wird von der Oberfläche `../carbon-footprint-ui` genutzt.

Technik: Python 3.10+, FastAPI, uvicorn, lxml, pydantic-settings, httpx2.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

## Starten

```bash
python -m carbon_footprint_api --aasx "../repo/*.aasx"
```

Swagger-Oberfläche: http://localhost:8080/api/docs, Status und Version: http://localhost:8080/api/health

Alle Optionen gibt es auch als Umgebungsvariable mit Präfix `CFA_` (Listen kommagetrennt). Die Kommandozeile hat
Vorrang.

| Option | Umgebungsvariable | Bedeutung |
|---|---|---|
| `--aasx MUSTER` | `CFA_AASX` | AASX-Dateien (Glob), mehrfach möglich |
| `--aas DATEIEN` | `CFA_AAS` | AAS-Dateien als XML oder JSON, kommagetrennt |
| `--checkReposNotEmpty` | `CFA_CHECK_REPOS_NOT_EMPTY` | Abbruch, wenn ein Muster keine Datei findet |
| `--port 8080` | `CFA_PORT` | Port |
| `--host 127.0.0.1` | `CFA_HOST` | Netzwerkschnittstelle (im Container `0.0.0.0`) |
| `--cors ORIGINS` | `CFA_CORS_ORIGINS` | Erlaubte Origins für `/api/v4/**` (nur nötig, wenn die Oberfläche unter einer anderen Adresse läuft) |
| `--static ORDNER` | `CFA_STATIC_DIR` | Statische Dateien ausliefern (z. B. gebaute Oberfläche) |
| `--notFoundResource /index.html` | `CFA_NOT_FOUND_RESOURCE` | Datei aus `--static` bei 404 (für Single-Page-Apps) |
| `--suppress404` | `CFA_SUPPRESS_404` | Dabei Status 200 statt 404 |
| `--logLevel INFO` | `CFA_LOG_LEVEL` | Log-Level |
| `--noDocs` | `CFA_DOCS_ENABLED=false` | Swagger abschalten |
| `--noExternalShells` | `CFA_EXTERNAL_SHELLS_ENABLED=false` | Laden von Dateien über URLs abschalten |
| | `CFA_EXTERNAL_MAX_BYTES` | Max. Größe heruntergeladener Dateien (Standard 50 MiB) |
| | `CFA_EXTERNAL_TIMEOUT_SECONDS` | Zeitlimit für Downloads (Standard 30 s) |
| | `CFA_EXTERNAL_MAX_CACHED` | Max. Anzahl gemerkter heruntergeladener Dateien (Standard 50) |
| | `CFA_MAX_ENTRY_BYTES` | Max. entpackte Größe eines Eintrags im AASX (Standard 256 MiB) |
| | `CFA_FORWARDED_ALLOW_IPS` | IPs von Reverse-Proxys, deren `X-Forwarded-*`-Header vertraut wird |

## Endpunkte

| Pfad | Inhalt |
|---|---|
| `GET /api/v4/shell-descriptors` | Alle (nicht versteckten) Shells als Deskriptoren |
| `GET /api/v4/shells/{id}` | Shell, `id` oder `globalAssetId` Base64-codiert (URL-sicher oder Standard) |
| `GET /api/v4/shells/{id}/submodel-refs` | Referenzen auf die Submodels |
| `GET /api/v4/shells/{id}/submodels/{smId}` | Submodel |
| `GET /api/v4/shells/{id}/submodels/{smId}/submodel-elements/{idShortPath}` | Element (`a.b[0].c`), unbekannter Pfad: 200 ohne Inhalt |
| `GET …/submodel-elements/{idShortPath}/attachment` | Datei eines File- oder Blob-Elements |
| `GET /api/v4/shells/{id}/asset-information/thumbnail` | Vorschaubild |
| `GET /api/v4/external-shells/{url}` | Shells aus einer Datei unter einer öffentlichen URL laden |
| `GET /api/v4/asset/all`, `/asset/{id}/submodel/all`, `/asset/{id}/submodel/{smId}` | Varianten mit nicht codierten IDs |
| `GET /api/v4/products/submodel-templates` | Unterstützte IDTA-Templates und Versionen |
| `GET /api/v4/products/{id}/templates` | Erkanntes Template, Version und Variante jedes Submodels einer Shell |
| `GET /api/v4/products/{id}/carbon-footprint` | Carbon Footprints aller Versionen, normalisiert, mit Zusammenfassung |
| `GET /api/v4/products/{id}/nameplate` | Hersteller und Adresse aus dem Typenschild |
| `GET /api/v4/products/{id}/technical-data` | Technische Daten mit Namen, Einheiten und Definitionen aus den ConceptDescriptions |
| `GET /api/v4/products/{id}/documentation` | Dokumente aus Handover Documentation / VDI 2770 |
| `GET /api/v4/products/{id}/maintenance` | Wartungsintervalle, -schritte, Werkzeuge, Verbrauchsmaterial, Ersatzteile |
| `GET /api/v4/products/{id}/details` | Alles zusammen: Templates, Typenschild, technische Daten, Dokumente, Wartung |
| `GET /api/v4/concept-descriptions/{cdId}` | ConceptDescription aus den geladenen Dateien (IRDIs auch mit anderem Versionsanhang) |
| `GET /api/v4/products/{id}/tree` | Produktbaum über alle Shells (Hierarchical Structures) mit Typenschild und Footprint |
| `GET /api/v4/search?q=…` | Volltextsuche in allen Shells und Submodels (idShorts, Werte, Texte); je Shell die ersten Fundstellen (`max_matches`, Standard 3) und deren Gesamtzahl. Heruntergeladene Shells nur mit `include={id}` |
| `GET /api/health` | Status, Version und Anzahl der Shells |

### Antwortformat

Die Shells und Submodels werden nicht im spezifikationskonformen AAS-JSON ausgegeben, sondern in dem Format, das die
Oberfläche erwartet: kein `modelType`, alle Felder auch mit `null`, Enums in CamelCase (`Instance`, `NotApplicable`,
`xs:string` als `String`), Submodel-Elemente nach Typ gruppiert. Fehler kommen als JSON mit `timestamp`, `status`,
`error`, `message` und `path`, sonstige HTTP-Fehler als Text (`Error 404 - Not Found`).

### Fachliche Endpunkte (`/products`)

`id` ist die `id` oder `globalAssetId` der Shell, Base64-codiert wie bei `/shells`. Die Antworten sind unabhängig von
der Template-Version der Datei. Unterstützt werden:

| Template | Versionen | Auswertung |
|---|---|---|
| Carbon Footprint (IDTA 02023) | 0.9, 1.0-Entwurf (Struktur 0.9 mit IDs 1/0), 1.0 bis 1.0.3 (Metamodell 3.0 und 3.1) | vollständig |
| Digital Battery Passport – Product Carbon Footprint (IDTA 02035-3) | 1.0 bis 1.0.2 | vollständig |
| Digital Nameplate (IDTA 02006), ZVEI Nameplate | 1.0, 2.0, 3.0 bis 3.0.3, HSU-Variante | Hersteller, Adresse |
| Digital Battery Passport – Digital Nameplate (IDTA 02035-1) | 1.0, 1.0.1 | Hersteller, Adresse |
| Contact Information (IDTA 02002) | 1.0 bis 1.0.4 | Adresse |
| Hierarchical Structures enabling BoM (IDTA 02011) | 1.0, 1.1 bis 1.1.4 | Produktbaum |
| Technical Data (IDTA 02003) | ZVEI 1.0, 1.1, 1.2, 1.2.1, Generic Frame 2.0 bis 2.0.4 | Allgemeines, Klassifikationen, Merkmale mit Einheit |
| Handover Documentation (IDTA 02004) | VDI 2770 1.0 (ZVEI), 1.2, 2.0 bis 2.0.4 | Dokumente, Versionen, Dateien |
| Maintenance Instructions (IDTA 02018) | 1.0 bis 1.0.2 | Intervalle, Schritte, Werkzeuge, Material, Ersatzteile |

Patch-Versionen (z. B. 1.0.1 → 1.0.3) sind in den Dateien nicht unterscheidbar (gleiche SemanticId und
Versionsangabe) und werden gemeinsam gelesen. IRDIs werden ohne Versionsanhang verglichen, Wert-IRDIs
(`0173-1#07-…`) in ihren Text übersetzt. Submodels ohne SemanticId werden über den idShort erkannt, leere
Template-Kopien ignoriert.

Zusammenfassung des Carbon Footprints (`summary`): Einträge werden nur innerhalb derselben Berechnungsmethode
addiert, jede Lebenszyklusphase zählt einmal (bei Überlappung wie A1-A3 neben A1, A2, A3 die feinere Aufteilung).
Hauptmethode ist ISO 14067, sonst GHG Protocol, EN 15804, ISO 14040/14044, sonst die zuerst genannte; die übrigen
stehen als Alternativen in `methods`. Transporte (TCF aus 0.9) werden als Phase A4 geführt und alle addiert.

Wiederholte Elemente werden unabhängig von der Schreibweise erkannt (`Document01`, `Document__00__`, `Document{00}`
oder Einträge einer SubmodelElementList). Namen, Einheiten und Wertelisten kommen aus den ConceptDescriptions der
geladenen Dateien.

### AAS- und AASX-Formate

Gelesen werden AAS-Environments nach Metamodell 3.0, 3.1 und 3.2 in XML und JSON sowie AASX-Pakete nach
IDTA-01005 3.0 bis 3.2 (Relationen mit und ohne `www.`, `data.xml`/`data.json` und `*.aas.xml`/`*.aas.json`).
Die Tests lesen alle gültigen Beispiele (`maximal`/`minimal` jeder Klasse) der neuesten Releases 3.0.9, 3.1.2 und
3.2.0 und prüfen, dass XML und JSON dasselbe ergeben und kein Attribut verloren geht (`tests/aas_format_examples.tar.gz`).
Neu in 3.2 und nur ausgegeben, wenn vorhanden: `createdAt`/`updatedAt` in `administration`; `DataSpecificationUom`
erscheint als eigener Inhaltstyp. AAS 2.0 (Wurzelelement `aasenv`) wird nicht gelesen.

Welche Template-Versionen bekannt sind, steht in `src/carbon_footprint_api/submodels/known_templates.json`. Neue
Versionen auf GitHub, auch neue Releases von Metamodell und AASX-Format, findet
`python tools/check_idta_templates.py` im Projektordner (siehe dort).

### Verhalten bei Datenfehlern

- AASX-Pakete mit fehlerhaften Relationen (z. B. umbenannte `.aas.xml`) werden über die vorhandene Environment-Datei
  geladen; beschädigte Dateien werden protokolliert und übersprungen.
- Doppelte ZIP-Einträge: der letzte gewinnt. Doppelte Submodel-ID bei einer Shell: das Duplikat wird übersprungen.
- Elemente ohne `idShort` werden bei der Pfadsuche übersprungen.

## Aufbau

```
src/carbon_footprint_api/
  aas/          Lesen von AAS-XML/-JSON/-AASX ins Antwortformat, Hilfsfunktionen
  submodels/    Versionsabhängige Parser der IDTA-Templates, normalisierte Modelle, Zusammenfassung
  repository/   Datenhaltung: Schnittstelle (AssetRepository) und In-Memory-Implementierung
  services/     Laden von Dateien über URLs (mit SSRF-Schutz und Cache), Produktsicht (Footprint, Produktbaum)
  api/          HTTP: Routen, Abhängigkeiten, Fehlerbehandlung, Middleware, statische Dateien
  config.py     Einstellungen (Kommandozeile und Umgebungsvariablen)
  main.py       Anwendungsfabrik create_app()
tests/          pytest, inkl. Snapshot-Vergleich aller Endpunkte (snapshots.tar.gz) und aller bekannten
                IDTA-Templates (idta_templates.tar.gz) und Formatbeispiele (aas_format_examples.tar.gz) von GitHub
tools/          record_snapshots.py zum Aufzeichnen der Referenzantworten
```

## Sicherheit

- `/external-shells` ruft nur öffentliche http(s)-Adressen ab (kein localhost, keine privaten oder link-lokalen
  Netze, auch nicht über Weiterleitungen oder DNS-Rebinding), mit Größen- und Zeitlimit. Heruntergeladene
  Shells ersetzen nie vorhandene und werden nach dem LRU-Prinzip wieder entfernt.
- AASX-Dateien werden mit Größenlimit je Eintrag gelesen (Zip-Bomben), XML ohne Entitäten und DTD (XXE).
- Attachments, die ein Browser ausführen könnte (HTML, SVG, XML, JavaScript), werden nur als Download mit
  `Content-Security-Policy: sandbox` ausgeliefert.
- Sicherheits-Header (`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`), kein `Server`-Header.
- CORS nur für die API, nur `GET`, ohne Credentials. Standardmäßig bindet der Server nur an `127.0.0.1`.

## Entwicklung

```bash
pytest          # Tests inkl. Snapshot-Vergleich (benötigt ../repo)
ruff check      # Linter inkl. Sicherheitsregeln
ruff format     # Formatierung
mypy            # Typprüfung
pip-audit       # bekannte Schwachstellen in Abhängigkeiten
```

Ändert sich das Antwortformat gewollt oder kommen Dateien in `../repo` hinzu, die Referenzantworten neu aufzeichnen
(API auf Port 8080 starten, dann):

```bash
python tools/record_snapshots.py http://localhost:8080 snapshots /api/v4
tar czf tests/snapshots.tar.gz snapshots
```

## Versionierung

Semantische Versionierung (`MAJOR.MINOR.PATCH`). Die Version steht nur in `src/carbon_footprint_api/__init__.py`
und wird bei jeder Änderung mit `python tools/bump_version.py api <major|minor|patch> "<Beschreibung>"`
(im Projektordner) erhöht, das Skript ergänzt auch die Changelogs. `MAJOR` steigt bei inkompatiblen Änderungen
der Endpunkte und bestimmt das Präfix (`/api/v4`). Ein Test prüft, dass der neueste Changelog-Eintrag zur Version
passt.

## Changelog

### 4.4.0 – 2026-11-15

- Parser für Technical Data (ZVEI 1.0 bis Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 bis 2.0.4) und Maintenance Instructions (1.0 bis 1.0.2) mit Endpunkten unter /products; ConceptDescriptions der Dateien werden gelesen und unter /concept-descriptions bereitgestellt; AAS-Metamodell 3.2 (createdAt/updatedAt, DataSpecificationUom) und AASX-Fallback auf data.xml/data.json
- Kompatibilitätstests mit allen gültigen Beispielen der Metamodell-Releases 3.0.9, 3.1.2 und 3.2.0 (XML und JSON)
  und den AASX-Beispielen 3.1/3.2
- Prüfskript meldet auch neue Releases von aas-specs-metamodel und aas-specs-aasx

### 4.3.0 – 2026-11-15

- Neuer Endpunkt /search: Volltextsuche in allen Shells und Submodels

### 4.2.0 – 2026-11-15

- Versionsunabhängige Parser für IDTA-Submodels: Carbon Footprint 0.9, 1.0-Entwurf und 1.0 bis 1.0.3 (Metamodell 3.0/3.1) inkl. Battery-Passport-PCF, Digital Nameplate 1.0 bis 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; Erkennung von Handover Documentation und Technical Data
- Neue Endpunkte unter `/api/v4/products`: erkannte Templates je Submodel, normalisierter Carbon Footprint mit
  Zusammenfassung je Berechnungsmethode, Typenschild und Produktbaum über alle Shells
- Wert-IRDIs aus ECLASS-Wertelisten werden in Text übersetzt; Submodels ohne SemanticId werden über den idShort
  erkannt, leere Template-Kopien ignoriert
- Tests gegen alle bekannten IDTA-Templates von GitHub (`tests/idta_templates.tar.gz`)

### 4.1.0 – 2026-11-15

- Betrieb als Docker-Container (python:3.13-slim, ohne Root-Rechte, schreibgeschütztes Dateisystem, Healthcheck über /api/health) mit docker-compose.yml; AASX-Dateien aus repo werden nach /opt/repo eingebunden

### 4.0.0 – 2026-11-15

- Neu implementiert in Python mit FastAPI als Ersatz der bisherigen Java-/Spring-Boot-Umsetzung; Antwortformat
  unverändert, damit die Oberfläche weiter funktioniert
- Inkompatibel: Präfix `/api/v4` statt `/api/v3.0`
- Neu: `/api/health`, Konfiguration über Umgebungsvariablen `CFA_*`, Optionen `--host`, `--logLevel`, `--noDocs`,
  `--noExternalShells`
- Neu: IDs werden auch im Standard-Base64 (wie `btoa` im Browser) angenommen, auch mit `/` im codierten Wert
- Sicherheit: SSRF-Schutz und Limits für `/external-shells`, keine Überschreibung vorhandener Shells durch Downloads,
  begrenzter Cache, Größenlimit für AASX-Einträge, sichere Auslieferung aktiver Attachments, Sicherheits-Header,
  CORS nur `GET` ohne Credentials, Standard-Bind auf `127.0.0.1`
- Korrigiert: Elemente ohne `idShort` führten zu HTTP 500; AASX mit fehlerhafter Relation wurde nicht geladen;
  unbekannte Shell bei Submodel- und Attachment-Abfragen liefert 404 statt 500; `--aas`-Dateien wurden doppelt
  geladen; idShorts mit `/` im Pfad
- Abhängigkeiten auf aktuellem Stand, ausschließlich freie Lizenzen (MIT, BSD, Apache-2.0, PSF)

### 0.0.1

- Ursprüngliche Umsetzung in Java (Spring Boot, Eclipse AAS4J) mit Präfix `/api/v3.0`
