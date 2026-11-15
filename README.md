# DPPviewer

Visuelle Analyse von Carbon Footprints aus Digitalen Produktpässen (Asset Administration Shells, AAS/AASX).
Hervorgegangen aus der Masterarbeit „Visual Analytics on Digital Product Passports to Optimize Production Chains“
im Forschungsprojekt CLiCE-DiPP, weitergeführt vom VIS-Team der Hochschule Darmstadt.

A public version is running at: https://dppviewer.policymodelling.com

## Bestandteile

| Ordner | Inhalt |
|---|---|
| [`carbon-footprint-api`](carbon-footprint-api/README.md) | REST-API (Python, FastAPI), liest AAS-/AASX-Dateien und stellt sie unter `/api/v4` bereit |
| [`carbon-footprint-ui`](carbon-footprint-ui/README.md) | Oberfläche (Vue, TypeScript, Vite) |
| `repo` | Beispiel- und Projektdateien (AASX), die die API beim Start lädt |
| `tools` | Hilfsskripte für das Gesamtprojekt (Versionierung, Prüfung auf neue IDTA-Templates) |

Die aktuellen Versionen stehen im Changelog der jeweiligen README und auf der About-Seite der Oberfläche.

## Schnellstart (Entwicklung)

Voraussetzungen: Python 3.10+, Node.js 20.19+.

```bash
# Terminal 1: API
cd carbon-footprint-api
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
python -m carbon_footprint_api --aasx "../repo/*.aasx"

# Terminal 2: Oberfläche
cd carbon-footprint-ui
npm install
npm run dev
```

Die Oberfläche läuft dann unter http://localhost:5173 und leitet `/api` an die API auf Port 8080 weiter.

## Versionierung

API und Oberfläche haben eigene Versionen nach [Semantic Versioning](https://semver.org/lang/de/). Jede Änderung
erhöht die Version des betroffenen Teils, die Stufe richtet sich nach der schwersten Änderung:

| Stufe | API | Oberfläche |
|---|---|---|
| `MAJOR` | Inkompatible Änderung an Endpunkten, Antwortformat, Optionen oder Umgebungsvariablen (neues Präfix `/api/vN`) | Benötigt eine neue Hauptversion der API, entfernte Ansichten oder Funktionen, Links oder gespeicherte Einstellungen werden ungültig |
| `MINOR` | Neue Endpunkte, Optionen oder Funktionen, abwärtskompatibel; neue Betriebsart (z. B. Container) | Neue Ansichten, Funktionen oder Einstellungen; sichtbare Gestaltungsänderungen |
| `PATCH` | Fehlerbehebungen, Sicherheitskorrekturen ohne Schnittstellenänderung, Aktualisierung von Abhängigkeiten, interne Umbauten | Fehlerbehebungen, Sicherheitskorrekturen, Aktualisierung von Abhängigkeiten, interne Umbauten |

Reine Dokumentationsänderungen erhöhen keine Version. Erhöht wird mit:

```bash
python tools/bump_version.py api patch "Kurze Beschreibung der Änderung"
python tools/bump_version.py ui minor "Kurze Beschreibung der Änderung"
```

Das Skript setzt die Version und trägt die Änderung in den Changelog des Teils und in den Changelog unten ein.
Tests der API und der Build der Oberfläche prüfen, dass Version und Changelog zusammenpassen.

| Oberfläche | benötigte API |
|---|---|
| 1.x | 4.x |

## IDTA-Submodel-Templates

Die API liest die IDTA-Submodels (Carbon Footprint, Digital Nameplate, Hierarchical Structures, Technical Data,
Handover Documentation, Maintenance Instructions u. a.) in allen bekannten Versionen sowie AAS/AASX nach Metamodell
3.0 bis 3.2, siehe [API-README](carbon-footprint-api/README.md#fachliche-endpunkte-products). Ob auf
[GitHub](https://github.com/admin-shell-io/submodel-templates/tree/main/published) neue Versionen erschienen sind,
und ob es neue Releases von [Metamodell](https://github.com/admin-shell-io/aas-specs-metamodel) oder
[AASX-Format](https://github.com/admin-shell-io/aas-specs-aasx) gibt, prüft:

```bash
python tools/check_idta_templates.py              # Bericht mit Strukturvergleich; Exit-Code 1 bei neuen Versionen
python tools/check_idta_templates.py --accept     # nach Anpassung der Parser: neue Versionen übernehmen
python tools/check_idta_templates.py --fixtures   # Testdaten (alle Templates) neu laden
```

## Lizenz

Apache License 2.0, siehe [LICENSE](LICENSE).

## Changelog

### 2026-11-15

- UI 1.2.5: Logo in der Kopfzeile mit dem Schriftzug „DPPviewer“ statt „CLiCE - DiPP“ (Datei src/assets/DPPviewer-logo.svg, Schrift Quicksand als Pfad)
- UI 1.2.4: Favicon und App-Symbole zeigen das CLiCE-DiPP-Logo (Lupe mit Blatt-Etikett)
- UI 1.2.4: Datasheet: lange Asset-Namen in der Kopfzeile werden gekürzt, der volle Name erscheint beim Überfahren
- UI 1.2.3: Datasheet scrollt bei vielen Assets waagerecht, die linke Spalte mit den Bezeichnungen bleibt dabei stehen
- UI 1.2.2: Datasheet zeigt alle Favoriten, auch ohne CO2-Daten (Zellen mit „no data“); ein nicht ladbares Asset blockiert nicht mehr das ganze Datasheet
- UI 1.2.2: Favoritenbox: Compare und Datasheet mit Symbolen, durch Linien vom Titel abgesetzt; Favoriten in einem eigenen, helleren Bereich
- UI 1.2.2: Statussymbol auf der Startseite rechts unten statt mittig unter den Favoriten
- UI 1.2.2: Fehlertabelle standardmäßig etwa ein Drittel der Fensterhöhe, kompaktere Zeilen, Scrollen ohne Mitscrollen der Seite
- UI 1.2.1: Karte der Übersicht schiebt sich beim Scrollen nicht mehr über die Kopfzeile
- UI 1.2.1: Doppelte Auswahl „More“ (Components, Life Cycles, Simulation) samt Symbol unter der Einzelansicht entfernt, die Navigation links genügt
- UI 1.2.1: Dunkelmodus: Beschriftungen und Linien der Diagramme in Overview, Components, Life Cycles und Simulation in der Schriftfarbe des Themas statt Schwarz; Adressfeld auf der Karte besser lesbar
- UI 1.2.1: Fehlertabelle höher (45 % der Fensterhöhe), am oberen Rand in der Höhe verstellbar, größere Schrift
- UI 1.2.1: Abweichende Berechnungen (CO2eq der Komponenten höher als das des Assets, fehlende Angabe Well-to-Tank/Tank-to-Wheel) erscheinen als Warnung statt als Fehler
- API 4.4.0: Parser für Technical Data (ZVEI 1.0 bis Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 bis 2.0.4) und Maintenance Instructions (1.0 bis 1.0.2) mit Endpunkten unter /products; ConceptDescriptions der Dateien werden gelesen und unter /concept-descriptions bereitgestellt; AAS-Metamodell 3.2 (createdAt/updatedAt, DataSpecificationUom) und AASX-Fallback auf data.xml/data.json
- UI 1.2.0: Neue Gestaltung: Kopfzeile mit Logo, Suche (optional innerhalb der Schalen), Hell/Dunkel und Info; linke Spalte entfällt
- UI 1.2.0: Favoriten per Drag-and-drop sortierbar, in der Favoritenbox die Analysen Compare (die ersten beiden Favoriten) und Datasheet (alle Favoriten); bisherige Favoriten werden übernommen
- UI 1.2.0: Compare als grafischer Vergleich zweier Assets nach dem Konzept der Thesis (Balken in zwei Richtungen um eine Nulllinie, Absolutwerte oder Differenz, Transport und Produkt je Lebenszyklusphase)
- UI 1.2.0: Datasheet ohne eigenes Hinzufügen von Schalen, kompakteres Layout; Summe der Lebenszyklusphasen aus Komponenten korrigiert (Stückzahlen wurden teils doppelt bzw. gar nicht berücksichtigt)
- UI 1.2.0: Klick auf eine Schale öffnet die Einzelansicht, die Auswahlschaltflächen beim Überfahren entfallen; gelber Rahmen nur noch bei Favoriten
- UI 1.2.0: Statussymbol (OK, Warnungen, Fehler mit Anzahl) unter den Favoriten, auf anderen Seiten unten rechts; Klick öffnet eine kompakte Tabelle, gleiche Meldungen werden zusammengefasst
- UI 1.2.0: Globale Fehlermeldung oben entfernt: Ladefehler erscheinen nur noch in der betroffenen Ansicht, auch wenn die Anfrage erst nach einem Seitenwechsel scheitert
- API 4.3.0: Neuer Endpunkt /search: Volltextsuche in allen Shells und Submodels
- API 4.2.0: Versionsunabhängige Parser für IDTA-Submodels: Carbon Footprint 0.9, 1.0-Entwurf und 1.0 bis 1.0.3 (Metamodell 3.0/3.1) inkl. Battery-Passport-PCF, Digital Nameplate 1.0 bis 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; Erkennung von Handover Documentation und Technical Data
- Prüfskript `tools/check_idta_templates.py` für neue Versionen der IDTA-Submodel-Templates auf GitHub; Hinweis in `CLAUDE.md`, es zu Beginn jeder Arbeitssitzung auszuführen
- UI 1.1.0: Betrieb als Docker-Container mit nginx: Weiterleitung von /api an die API, Laufzeitkonfiguration und Content-Security-Policy aus Umgebungsvariablen, Sicherheits-Header, Caching, Begrenzung der Downloads über URLs; Adresssuche mit GEOCODING_URL=off abschaltbar
- API 4.1.0: Betrieb als Docker-Container (python:3.13-slim, ohne Root-Rechte, schreibgeschütztes Dateisystem, Healthcheck über /api/health) mit docker-compose.yml; AASX-Dateien aus repo werden nach /opt/repo eingebunden
- API 4.0.0: Neuimplementierung in Python (FastAPI) mit Präfix `/api/v4`, Konfiguration über Umgebungsvariablen,
  Sicherheitsüberarbeitung
- UI 1.0.0: umbenannt in `carbon-footprint-ui`, Leaflet/OpenStreetMap statt Mapbox, CLiCE-DiPP-Logo, aktuelle
  Bibliotheken, zahlreiche Fehlerbehebungen, Versionsanzeige
- Projekt aufgeräumt: Java-Umsetzung der API und alter Frontend-Ordner `carbon-trace-main` entfernt, Versionierung
  und Changelogs eingeführt
