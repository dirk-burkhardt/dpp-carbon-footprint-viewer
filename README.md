# DPPviewer

Visuelle Analyse von Carbon Footprints aus Digitalen Produktpässen (Asset Administration Shells, AAS/AASX).
Hervorgegangen aus der Masterarbeit „Visual Analytics on Digital Product Passports to Optimize Production Chains“
im Forschungsprojekt CLiCE-DiPP, weitergeführt vom VIS-Team der Hochschule Darmstadt.

## Bestandteile

| Ordner | Inhalt |
|---|---|
| [`carbon-footprint-api`](carbon-footprint-api/README.md) | REST-API (Python, FastAPI), liest AAS-/AASX-Dateien und stellt sie unter `/api/v4` bereit |
| [`carbon-footprint-ui`](carbon-footprint-ui/README.md) | Oberfläche (Vue, TypeScript, Vite) |
| `repo` | Beispiel- und Projektdateien (AASX), die die API beim Start lädt |
| `tools` | Hilfsskripte für das Gesamtprojekt (z. B. Versionierung) |

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

API und Oberfläche haben eigene Versionen nach [Semantic Versioning](https://semver.org/lang/de/):
`MAJOR` bei inkompatiblen Änderungen, `MINOR` bei neuen Funktionen, `PATCH` bei Fehlerbehebungen. Jede Änderung
erhöht die Version des betroffenen Teils:

```bash
python tools/bump_version.py api patch "Kurze Beschreibung der Änderung"
python tools/bump_version.py ui minor "Kurze Beschreibung der Änderung"
```

Das Skript setzt die Version und trägt die Änderung in den Changelog des Teils und in den Changelog unten ein.
Tests der API und der Build der Oberfläche prüfen, dass Version und Changelog zusammenpassen.

| Oberfläche | benötigte API |
|---|---|
| 1.x | 4.x |

## Lizenz

Apache License 2.0, siehe [LICENSE](LICENSE).

## Changelog

### 2026-11-15

- API 4.0.0: Neuimplementierung in Python (FastAPI) mit Präfix `/api/v4`, Konfiguration über Umgebungsvariablen,
  Sicherheitsüberarbeitung
- UI 1.0.0: umbenannt in `carbon-footprint-ui`, Leaflet/OpenStreetMap statt Mapbox, CLiCE-DiPP-Logo, aktuelle
  Bibliotheken, zahlreiche Fehlerbehebungen, Versionsanzeige
- Projekt aufgeräumt: Java-Umsetzung der API und alter Frontend-Ordner `carbon-trace-main` entfernt, Versionierung
  und Changelogs eingeführt
