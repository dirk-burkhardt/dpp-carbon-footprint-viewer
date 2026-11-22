# DPPviewer

Visual analysis of carbon footprints from digital product passports (Asset Administration Shells, AAS/AASX).
Originates from the master's thesis "Visual Analytics on Digital Product Passports to Optimize Production Chains"
in the research project CLiCE-DiPP and is continued by the VIS team of Darmstadt University of Applied Sciences
(Hochschule Darmstadt).

A public version is running at: https://dppviewer.policymodelling.com

## Components

| Folder | Content |
|---|---|
| [`carbon-footprint-api`](carbon-footprint-api/README.md) | REST API (Python, FastAPI) that reads AAS/AASX files and provides them under `/api/v4` |
| [`carbon-footprint-ui`](carbon-footprint-ui/README.md) | User interface (Vue, TypeScript, Vite) |
| `repo` | Sample and project files (AASX) that the API loads on startup; `repo/uploads` takes uploaded files |
| `tools` | Helper scripts for the whole project (versioning, check for new IDTA templates) |
| `docs` | Concepts, e.g. the [strategy for Technical Data and Hierarchical Structures](docs/strategy-technical-data-and-hierarchy.md) |

The current versions are listed in the respective `CHANGELOG.md` and on the About page of the user interface.

## Quick start (Docker, local)

Requirements: Docker with the Compose plugin (Docker Desktop on Windows/macOS, Docker Engine on Linux).

```bash
cp .env.example .env               # Windows: copy .env.example .env
mkdir -p repo/uploads              # folder for uploaded files
sudo chown 10001 repo/uploads      # Linux only: the API container runs as user 10001
docker compose up -d --build       # build the images and start both containers
docker compose ps                  # status, the API reports healthy after a few seconds
docker compose logs -f             # follow the logs (Ctrl+C only stops the output)
docker compose down                # stop
```

The API loads the AASX files in `repo` on startup (only files directly in the folder, no subfolders). Uploaded
files are stored in `repo/uploads`, separate from the static files; they are deleted after `UPLOAD_TTL_HOURS` and
on every restart. If the folder is not writable, the API keeps uploads in memory only and reports this in its log.
After changes in `repo`, `docker compose restart api` is sufficient; after changes to the source code run
`docker compose up -d --build`.

Settings in `.env` (all optional, see the comments in `.env.example`):

| Variable | Default | Meaning |
|---|---|---|
| `UI_PORT` | `5001` | Port on the host under which the user interface is available |
| `API_LOG_LEVEL` | `INFO` | Log level of the API |
| `API_DOCS_ENABLED` | `true` | Provide the Swagger UI and the OpenAPI description |
| `API_EXTERNAL_SHELLS_ENABLED` | `true` | Allow loading AASX files from a URL |
| `UPLOADS_ENABLED` | `true` | Allow uploading AAS(X) files in the user interface |
| `UPLOAD_MAX_MB` | `25` | Maximum size of an uploaded file in MB |
| `UPLOAD_TTL_HOURS` | `3` | Hours after which uploaded files and files loaded from links are discarded (uploads at the latest on a restart of the API) |
| `MAP_TILE_URL`, `MAP_ATTRIBUTION`, `GEOCODING_URL` | empty | Map tiles and address search, empty = OpenStreetMap/Nominatim, `GEOCODING_URL=off` disables the address search |

Available in the browser (with the default port 5001):

| Address | Content |
|---|---|
| http://localhost:5001 | User interface: asset selection, single asset view, Compare, Datasheet |
| http://localhost:5001/about | About page with the versions of user interface and API |
| http://localhost:5001/api/docs | Swagger UI of the API (only with `API_DOCS_ENABLED=true`) |
| http://localhost:5001/api/openapi.json | OpenAPI description of the API (only with `API_DOCS_ENABLED=true`) |
| http://localhost:5001/api/health | State of the API with version and number of loaded shells |
| http://localhost:5001/api/v4/shells | Example of a domain endpoint: all loaded shells as JSON |

The API has no port of its own to the outside; it is only reachable through the user interface under `/api`.
There is no administration interface, all settings are made in `.env`.

## Quick start (development)

Requirements: Python 3.10+, Node.js 20.19+.

```bash
# Terminal 1: API
cd carbon-footprint-api
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
python -m carbon_footprint_api --aasx "../repo/*.aasx" --uploadDir ../repo/uploads

# Terminal 2: user interface
cd carbon-footprint-ui
npm install
npm run dev
```

The user interface then runs at http://localhost:5173 and forwards `/api` to the API on port 8080.

## Versioning

API and user interface have their own versions following [Semantic Versioning](https://semver.org/). Every change
raises the version of the affected part; the level depends on the most severe change:

| Level | API | User interface |
|---|---|---|
| `MAJOR` | Incompatible change of endpoints, response format, options or environment variables (new prefix `/api/vN`) | Requires a new major version of the API; removed views or functions; links or stored settings become invalid |
| `MINOR` | New endpoints, options or functions, backwards compatible; new mode of operation (e.g. container) | New views, functions or settings; visible design changes |
| `PATCH` | Bug fixes, security fixes without interface changes, dependency updates, internal refactoring | Bug fixes, security fixes, dependency updates, internal refactoring |

Changes to the documentation only do not raise a version. Versions are raised with:

```bash
python tools/bump_version.py api patch "Short description of the change"
python tools/bump_version.py ui minor "Short description of the change"
```

The script sets the version and adds the change to the `CHANGELOG.md` of the part and to that of the whole project.
The API tests and the build of the user interface check that version and changelog match.

| User interface | Required API |
|---|---|
| 1.x | 4.x |

## IDTA submodel templates

The API reads the IDTA submodels (Carbon Footprint, Digital Nameplate, Hierarchical Structures, Technical Data,
Handover Documentation, Maintenance Instructions and others) in all known versions as well as AAS/AASX according to
metamodel 3.0 to 3.2, see the [API README](carbon-footprint-api/README.md#domain-endpoints-products). Whether new
versions have been published on [GitHub](https://github.com/admin-shell-io/submodel-templates/tree/main/published),
and whether there are new releases of the [metamodel](https://github.com/admin-shell-io/aas-specs-metamodel) or the
[AASX format](https://github.com/admin-shell-io/aas-specs-aasx), is checked by:

```bash
python tools/check_idta_templates.py              # report with structure comparison; exit code 1 for new versions
python tools/check_idta_templates.py --accept     # after adapting the parsers: accept the new versions
python tools/check_idta_templates.py --fixtures   # download the test data (all templates) again
```

## License

Apache License 2.0, see [LICENSE](LICENSE).

## Changelog

All changes are listed in [CHANGELOG.md](CHANGELOG.md), the details per part in the changelogs of the
[API](carbon-footprint-api/CHANGELOG.md) and the [user interface](carbon-footprint-ui/CHANGELOG.md).
