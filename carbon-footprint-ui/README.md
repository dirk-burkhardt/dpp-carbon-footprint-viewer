# Carbon-Footprint-UI

Oberfläche des DPPviewer zur Analyse von Carbon Footprints aus Asset Administration Shells (AAS/AASX). Sie
benötigt die Carbon-Footprint-API (`../carbon-footprint-api`) in Version 4.x.

Technik: Vue 3, TypeScript, Vite, Tailwind CSS 4 mit daisyUI 5, Observable Plot und d3 für Diagramme,
Leaflet mit OpenStreetMap für Karten. Alle Abhängigkeiten stehen unter freien Lizenzen (MIT, ISC, BSD,
Apache-2.0; Lightning CSS unter MPL-2.0, nur beim Bauen).

## Voraussetzungen

Node.js 20.19 oder neuer (empfohlen: 22 LTS oder 24 LTS).

## Einrichtung und Entwicklung

```sh
npm install
npm run dev
```

Der Entwicklungsserver läuft unter http://localhost:5173 und leitet `/api` an die API weiter
(Standard `http://localhost:8080`, änderbar über die Umgebungsvariable `API_PROXY_TARGET`). Die API muss
dafür laufen, CORS ist nicht nötig.

## Weitere Befehle

| Befehl | Zweck |
|---|---|
| `npm run build` | Versionsprüfung, Typcheck und Produktions-Build nach `dist/` |
| `npm run check-version` | Prüft, ob die Version in `package.json` im Changelog steht |
| `npm run type-check` | Nur Typcheck (vue-tsc) |
| `npm run lint` | ESLint mit automatischen Korrekturen |
| `npm run format` | Prettier |
| `npm run generate` | API-Typen aus den Swagger-Dateien in `src/assets/api` neu erzeugen |

## Konfiguration

Standardwerte stehen in `.env` und werden beim Bauen eingesetzt. Zur Laufzeit können sie über
`/config.json` überschrieben werden (leere Werte werden ignoriert):

| Schlüssel in `config.json` | Variable in `.env` | Standard |
|---|---|---|
| `assetAdministrationShellRegistryUrl` | `VITE_API_ASSET_ADMINISTRATION_SHELL_REGISTRY_URL` | `/api/v4` |
| `assetAdministrationShellRepositoryUrl` | `VITE_API_ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL` | `/api/v4` |
| `assetAdministrationShellSubmodelRepositoryUrl` | `VITE_API_SUBMODEL_REPOSITORY_URL` | `/api/v4` |
| `assetAdministrationShellAdditionalsUrl` | `VITE_API_ASSET_ADDITIONALS_URL` | `/api/v4` |
| `preferSubmodelRepository` | `VITE_API_PREFER_SUBMODELS_REPOSITORY` | `0` |
| `mapTileUrl` | `VITE_MAP_TILE_URL` | OpenStreetMap-Kacheln |
| `mapAttribution` | `VITE_MAP_ATTRIBUTION` | © OpenStreetMap |
| `geocodingUrl` | `VITE_GEOCODING_URL` | `https://nominatim.openstreetmap.org` (leer = aus) |

### Karten und Adresssuche

Karten nutzen Leaflet mit OpenStreetMap-Kacheln, Adressen werden über Nominatim in Koordinaten
umgewandelt (höchstens eine Anfrage pro Sekunde, Ergebnisse werden 30 Tage im Browser gespeichert).
Die öffentlichen OpenStreetMap-Server sind nur für geringe Last gedacht und verlangen die Namensnennung,
die Leaflet in der Karte anzeigt. Für einen produktiven Betrieb mit vielen Nutzern eigene Kachel- und
Nominatim-Server eintragen. Beim Geocoding werden Adressdaten der angezeigten Assets an den
Geocoding-Dienst übertragen.

## Versionierung

Semantische Versionierung (`MAJOR.MINOR.PATCH`). Die Version steht nur in `package.json`, wird beim Bauen
eingesetzt und auf der About-Seite zusammen mit der Version der API angezeigt. Bei jeder Änderung im
Projektordner `python tools/bump_version.py ui <major|minor|patch> "<Beschreibung>"` ausführen; das Skript
erhöht die Version und ergänzt die Changelogs. `npm run build` bricht ab, wenn Version und Changelog nicht
zusammenpassen.

| UI | benötigte API |
|---|---|
| 1.x | 4.x (`/api/v4`) |

## Docker

Das `Dockerfile` baut die Oberfläche und liefert sie mit nginx aus (ohne Root-Rechte, schreibgeschütztes
Dateisystem). nginx leitet `/api` an die API weiter und erzeugt beim Start die Laufzeitkonfiguration
(`/config.json`) und die Content-Security-Policy aus den Umgebungsvariablen `API_UPSTREAM`, `MAP_TILE_URL`,
`MAP_ATTRIBUTION`, `GEOCODING_URL` sowie `ASSET_ADMINISTRATION_SHELL_*_URL` und `PREFER_SUBMODELS_REPOSITORY`.
Gestartet wird zusammen mit der API über `docker-compose.yml` im Projektordner, siehe
[Schnellstart (Docker, lokal)](../README.md#schnellstart-docker-lokal).

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).
