# Carbon Footprint UI

User interface of the DPPviewer for analysing carbon footprints from Asset Administration Shells (AAS/AASX). It
requires the Carbon Footprint API (`../carbon-footprint-api`) in version 4.x.

Technology: Vue 3, TypeScript, Vite, Tailwind CSS 4 with daisyUI 5, Observable Plot and d3 for charts, Leaflet
with OpenStreetMap for maps. All dependencies are under free licenses (MIT, ISC, BSD, Apache-2.0; Lightning CSS
under MPL-2.0, only at build time).

## Requirements

Node.js 20.19 or newer (recommended: 22 LTS or 24 LTS).

## Setup and development

```sh
npm install
npm run dev
```

The development server runs at http://localhost:5173 and forwards `/api` to the API (default
`http://localhost:8080`, can be changed with the environment variable `API_PROXY_TARGET`). The API has to be
running; CORS is not needed.

## Further commands

| Command | Purpose |
|---|---|
| `npm run build` | Version check, type check and production build into `dist/` |
| `npm run check-version` | Checks whether the version in `package.json` is in the changelog |
| `npm run type-check` | Type check only (vue-tsc) |
| `npm run lint` | ESLint with automatic fixes |
| `npm run format` | Prettier |
| `npm run generate` | Generate the API types again from the Swagger files in `src/assets/api` |

## Configuration

Default values are in `.env` and are set at build time. At runtime they can be overridden through `/config.json`
(empty values are ignored):

| Key in `config.json` | Variable in `.env` | Default |
|---|---|---|
| `assetAdministrationShellRegistryUrl` | `VITE_API_ASSET_ADMINISTRATION_SHELL_REGISTRY_URL` | `/api/v4` |
| `assetAdministrationShellRepositoryUrl` | `VITE_API_ASSET_ADMINISTRATION_SHELL_REPOSITORY_URL` | `/api/v4` |
| `assetAdministrationShellSubmodelRepositoryUrl` | `VITE_API_SUBMODEL_REPOSITORY_URL` | `/api/v4` |
| `assetAdministrationShellAdditionalsUrl` | `VITE_API_ASSET_ADDITIONALS_URL` | `/api/v4` |
| `preferSubmodelRepository` | `VITE_API_PREFER_SUBMODELS_REPOSITORY` | `0` |
| `mapTileUrl` | `VITE_MAP_TILE_URL` | OpenStreetMap tiles |
| `mapAttribution` | `VITE_MAP_ATTRIBUTION` | © OpenStreetMap |
| `geocodingUrl` | `VITE_GEOCODING_URL` | `https://nominatim.openstreetmap.org` (empty = off) |

### Maps and address search

Maps use Leaflet with OpenStreetMap tiles; addresses are converted into coordinates through Nominatim (at most one
request per second, results are kept in the browser for 30 days). The public OpenStreetMap servers are only meant
for low load and require the attribution that Leaflet shows in the map. For productive use with many users, enter
your own tile and Nominatim servers. Geocoding sends address data of the displayed assets to the geocoding service.

## Versioning

Semantic versioning (`MAJOR.MINOR.PATCH`). The version is only stored in `package.json`, set at build time and
shown on the About page together with the version of the API. With every change run
`python tools/bump_version.py ui <major|minor|patch> "<description>"` in the project folder; the script raises the
version and updates the changelogs. `npm run build` fails if version and changelog do not match.

| UI | Required API |
|---|---|
| 1.x | 4.x (`/api/v4`) |

## Docker

The `Dockerfile` builds the user interface and serves it with nginx (without root privileges, read-only file
system). nginx forwards `/api` to the API and creates the runtime configuration (`/config.json`) and the Content
Security Policy on startup from the environment variables `API_UPSTREAM`, `MAP_TILE_URL`, `MAP_ATTRIBUTION`,
`GEOCODING_URL`, `UPLOAD_MAX_MB` as well as `ASSET_ADMINISTRATION_SHELL_*_URL` and `PREFER_SUBMODELS_REPOSITORY`. It
is started together with the API through `docker-compose.yml` in the project folder, see
[Quick start (Docker, local)](../README.md#quick-start-docker-local).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
