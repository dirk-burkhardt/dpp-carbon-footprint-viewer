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

Die aktuellen Versionen stehen im jeweiligen `CHANGELOG.md` und auf der About-Seite der Oberfläche.

## Schnellstart (Docker, lokal)

Voraussetzungen: Docker mit Compose-Plugin (Docker Desktop unter Windows/macOS, Docker Engine unter Linux).

```bash
cp .env.example .env               # Windows: copy .env.example .env
docker compose up -d --build       # Images bauen und beide Container starten
docker compose ps                  # Status, die API meldet sich nach einigen Sekunden als healthy
docker compose logs -f             # Protokolle verfolgen (Strg+C beendet nur die Anzeige)
docker compose down                # beenden
```

Die API lädt die AASX-Dateien aus `repo` beim Start. Nach Änderungen dort genügt `docker compose restart api`,
nach Änderungen am Quellcode `docker compose up -d --build`.

In `.env` lassen sich anpassen (alle Angaben sind optional, siehe Kommentare in `.env.example`):

| Variable | Standard | Bedeutung |
|---|---|---|
| `UI_PORT` | `5001` | Port auf dem Rechner, unter dem die Oberfläche erreichbar ist |
| `API_LOG_LEVEL` | `INFO` | Protokollstufe der API |
| `API_DOCS_ENABLED` | `true` | Swagger-Oberfläche und OpenAPI-Beschreibung bereitstellen |
| `API_EXTERNAL_SHELLS_ENABLED` | `true` | Laden von AASX-Dateien über eine URL erlauben |
| `UPLOADS_ENABLED` | `true` | Hochladen von AAS(X)-Dateien in der Oberfläche erlauben |
| `UPLOAD_MAX_MB` | `25` | Maximale Größe einer hochgeladenen Datei in MB |
| `UPLOAD_TTL_HOURS` | `3` | Stunden, nach denen hochgeladene Dateien gelöscht werden (spätestens beim Neustart der API) |
| `MAP_TILE_URL`, `MAP_ATTRIBUTION`, `GEOCODING_URL` | leer | Kartenkacheln und Adresssuche, leer = OpenStreetMap/Nominatim, `GEOCODING_URL=off` schaltet die Adresssuche ab |

Im Browser erreichbar (mit Standardport 5001):

| Adresse | Inhalt |
|---|---|
| http://localhost:5001 | Oberfläche: Auswahl der Assets, Einzelansicht, Compare, Datasheet |
| http://localhost:5001/about | Info-Seite mit den Versionen von Oberfläche und API |
| http://localhost:5001/api/docs | Swagger-Oberfläche der API (nur mit `API_DOCS_ENABLED=true`) |
| http://localhost:5001/api/openapi.json | OpenAPI-Beschreibung der API (nur mit `API_DOCS_ENABLED=true`) |
| http://localhost:5001/api/health | Zustand der API mit Version und Anzahl geladener Shells |
| http://localhost:5001/api/v4/shells | Beispiel eines fachlichen Endpunkts: alle geladenen Shells als JSON |

Die API hat keinen eigenen Port nach außen, sie ist nur über die Oberfläche unter `/api` erreichbar. Eine
Verwaltungsoberfläche gibt es nicht, Einstellungen erfolgen ausschließlich über `.env`.

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

Das Skript setzt die Version und trägt die Änderung in das `CHANGELOG.md` des Teils und in das des Gesamtprojekts ein.
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

Alle Änderungen stehen in [CHANGELOG.md](CHANGELOG.md), die Einzelheiten je Teil in den Changelogs von [API](carbon-footprint-api/CHANGELOG.md) und [Oberfläche](carbon-footprint-ui/CHANGELOG.md).
