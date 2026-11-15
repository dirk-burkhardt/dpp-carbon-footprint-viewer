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

Die Container-Umstellung (API und Frontend mit nginx) folgt. Das bisherige `Dockerfile` schreibt die
Laufzeitkonfiguration über `run.sh` aus den Umgebungsvariablen `ASSET_ADMINISTRATION_SHELL_*_URL`,
`PREFER_SUBMODELS_REPOSITORY`, `MAP_TILE_URL`, `MAP_ATTRIBUTION` und `GEOCODING_URL`.

## Changelog

### 1.0.0 – 2026-11-15

- Umbenannt von `carbon-trace` in `carbon-footprint-ui`, Logo oben links ist jetzt das CLiCE-DiPP-Logo
- Inkompatibel: nutzt die API 4.x unter `/api/v4`; im Entwicklungsbetrieb leitet Vite `/api` an die API weiter
- Karten mit Leaflet und OpenStreetMap, Adresssuche über Nominatim statt Mapbox (keine kommerzielle Lizenz und kein
  Zugangstoken mehr nötig)
- Versionsanzeige von Oberfläche und API auf der About-Seite
- Aktualisiert: Vue 3.5, vue-router 5, Vite 8, Tailwind CSS 4, daisyUI 5, TypeScript 6, ESLint 10; ungenutzte
  Pakete entfernt (ECharts, pako, htl)
- Korrigiert: Transport-Footprints wurden in der Simulation verworfen; falsche Tooltips im Änderungsdiagramm bei
  aktivem Filter; Brotkrümel der Zwei-Asset-Ansicht; IDs mit Umlauten und Sonderzeichen; fehlgeschlagene
  Anfragen blieben bis zum Neuladen gespeichert; Erkennung des Dunkelmodus; fett gesetzte Namen in Tooltips;
  Simulationslink
- Sicherheit: Attachment-Pfade werden codiert, externe Links mit `noopener`, keine Zugangsdaten im Code,
  `npm audit` ohne Befund
- Ansichten werden erst bei Bedarf geladen (Startpaket 378 statt 995 KB), Typcheck und Lint ohne Fehler

### 0.0.0

- Ursprüngliche Oberfläche `carbon-trace` (Vue 3, Vite 5, Tailwind CSS 3, Mapbox)
