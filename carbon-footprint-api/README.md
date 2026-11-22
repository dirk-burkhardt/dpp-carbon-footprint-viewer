# Carbon Footprint API

REST interface of the DPPviewer. Provides Asset Administration Shells from AAS and AASX files (folder `../repo`)
under `/api/v4` and is used by the user interface `../carbon-footprint-ui`.

Technology: Python 3.10+, FastAPI, uvicorn, lxml, pydantic-settings, httpx2.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
python -m carbon_footprint_api --aasx "../repo/*.aasx"
```

Swagger UI: http://localhost:8080/api/docs, status and version: http://localhost:8080/api/health

All options are also available as environment variables with the prefix `CFA_` (lists comma separated). The
command line takes precedence.

| Option | Environment variable | Meaning |
|---|---|---|
| `--aasx PATTERN` | `CFA_AASX` | AASX files (glob), can be given several times |
| `--aas FILES` | `CFA_AAS` | AAS files as XML or JSON, comma separated |
| `--checkReposNotEmpty` | `CFA_CHECK_REPOS_NOT_EMPTY` | Abort if a pattern matches no file |
| `--port 8080` | `CFA_PORT` | Port |
| `--host 127.0.0.1` | `CFA_HOST` | Network interface (`0.0.0.0` in the container) |
| `--cors ORIGINS` | `CFA_CORS_ORIGINS` | Allowed origins for `/api/v4/**` (only needed if the user interface runs under another address) |
| `--static FOLDER` | `CFA_STATIC_DIR` | Serve static files (e.g. the built user interface) |
| `--notFoundResource /index.html` | `CFA_NOT_FOUND_RESOURCE` | File from `--static` served for 404 (single-page apps) |
| `--suppress404` | `CFA_SUPPRESS_404` | Respond with status 200 instead of 404 in that case |
| `--logLevel INFO` | `CFA_LOG_LEVEL` | Log level |
| `--noDocs` | `CFA_DOCS_ENABLED=false` | Disable Swagger |
| `--noExternalShells` | `CFA_EXTERNAL_SHELLS_ENABLED=false` | Disable loading files from URLs |
| | `CFA_EXTERNAL_MAX_BYTES` | Maximum size of downloaded files (default 50 MiB) |
| | `CFA_EXTERNAL_TIMEOUT_SECONDS` | Timeout for downloads (default 30 s) |
| | `CFA_EXTERNAL_MAX_CACHED` | Maximum number of remembered downloaded files (default 50) |
| `--noUploads` | `CFA_UPLOADS_ENABLED=false` | Disable uploads |
| `--uploadMaxMb` | `CFA_UPLOAD_MAX_MB` | Maximum size of an uploaded file in MB (default 25) |
| `--uploadTtlHours` | `CFA_UPLOAD_TTL_HOURS` | Hours after which an upload is deleted (default 3) |
| `--uploadDir` | `CFA_UPLOAD_DIR` | Folder for uploaded files, e.g. `../repo/uploads` (default: memory only). Uploads of earlier runs are deleted there on startup, other files are left untouched |
| | `CFA_UPLOAD_MAX_COUNT` | Maximum number of uploads kept at the same time, the oldest are removed (default 20) |
| | `CFA_MAX_ENTRY_BYTES` | Maximum unpacked size of an entry in an AASX (default 256 MiB) |
| | `CFA_FORWARDED_ALLOW_IPS` | IPs of reverse proxies whose `X-Forwarded-*` headers are trusted |

## Endpoints

| Path | Content |
|---|---|
| `GET /api/v4/shell-descriptors` | All (not hidden) shells as descriptors |
| `GET /api/v4/shells/{id}` | Shell, `id` or `globalAssetId` Base64 encoded (URL safe or standard) |
| `GET /api/v4/shells/{id}/submodel-refs` | References to the submodels |
| `GET /api/v4/shells/{id}/submodels/{smId}` | Submodel |
| `GET /api/v4/shells/{id}/submodels/{smId}/submodel-elements/{idShortPath}` | Element (`a.b[0].c`), unknown path: 200 without content |
| `GET …/submodel-elements/{idShortPath}/attachment` | File of a File or Blob element |
| `GET /api/v4/shells/{id}/asset-information/thumbnail` | Thumbnail |
| `GET /api/v4/external-shells/{url}` | Load shells from a file at a public URL; discarded after `CFA_UPLOAD_TTL_HOURS` and loaded again on the next request |
| `GET /api/v4/uploads` | Whether uploads are possible, maximum size (`maxBytes`) and retention (`ttlSeconds`) |
| `POST /api/v4/uploads?filename=…` | Upload a file (`.aasx`, `.aas.json`, `.aas.xml`) as request body; the response contains `id`, `expiresAt` and the shells. Stored in `CFA_UPLOAD_DIR`, deleted after expiry, when `CFA_UPLOAD_MAX_COUNT` is exceeded and on every restart |
| `GET /api/v4/uploads/{uploadId}` | Upload with its shells, 404 after expiry |
| `DELETE /api/v4/uploads/{uploadId}` | Delete an upload before it expires |
| `GET /api/v4/asset/all`, `/asset/{id}/submodel/all`, `/asset/{id}/submodel/{smId}` | Variants with unencoded IDs |
| `GET /api/v4/products/submodel-templates` | Supported IDTA templates and versions |
| `GET /api/v4/products/{id}/templates` | Detected template, version and variant of every submodel of a shell |
| `GET /api/v4/products/{id}/carbon-footprint` | Carbon footprints of all versions, normalized, with summary |
| `GET /api/v4/products/{id}/nameplate` | Manufacturer and address from the nameplate |
| `GET /api/v4/products/{id}/technical-data` | Technical data with names, units and definitions from the ConceptDescriptions |
| `GET /api/v4/products/{id}/indicators` | Reference quantities from Technical Data in SI units (mass in kg, power in W, service life in years, dimensions in m, volume) with their source, and material information; recognizes ECLASS IDs, common names, units within the value (`"2,250 g"`) and stroke dependent masses of cylinders; `technicalDataFound` tells whether the shell has Technical Data at all |
| `GET /api/v4/products/{id}/estimates` | Estimates for life cycle phases without declared footprint (see below), parameters `country`, `lifetimeYears`, `hoursPerYear`, `transportKm`, `transportMode` |
| `GET /api/v4/products/{id}/documentation` | Documents from Handover Documentation / VDI 2770 |
| `GET /api/v4/products/{id}/maintenance` | Maintenance intervals, steps, tools, consumables, spare parts |
| `GET /api/v4/products/{id}/details` | Everything together: templates, nameplate, technical data, documents, maintenance |
| `GET /api/v4/concept-descriptions/{cdId}` | ConceptDescription from the loaded files (IRDIs also with another version suffix) |
| `GET /api/v4/products/{id}/tree` | Product tree across all shells (Hierarchical Structures) with nameplate and footprint |
| `GET /api/v4/search?q=…` | Full-text search in all shells and submodels (idShorts, values, texts); per shell the first matches (`max_matches`, default 3) and their total number. Downloaded shells only with `include={id}` |
| `GET /api/health` | Status, version and number of shells |

### Response format

Shells and submodels are not returned in the specification-compliant AAS JSON but in the format the user interface
expects: no `modelType`, all fields present also with `null`, enums in CamelCase (`Instance`, `NotApplicable`,
`xs:string` as `String`), submodel elements grouped by type. Errors are returned as JSON with `timestamp`,
`status`, `error`, `message` and `path`, other HTTP errors as text (`Error 404 - Not Found`).

### Domain endpoints (`/products`)

`id` is the `id` or `globalAssetId` of the shell, Base64 encoded as for `/shells`. The responses do not depend on
the template version used in the file. Supported are:

| Template | Versions | Evaluation |
|---|---|---|
| Carbon Footprint (IDTA 02023) | 0.9, 1.0 draft (structure of 0.9 with IDs 1/0), 1.0 to 1.0.3 (metamodel 3.0 and 3.1) | complete |
| Digital Battery Passport – Product Carbon Footprint (IDTA 02035-3) | 1.0 to 1.0.2 | complete |
| Digital Nameplate (IDTA 02006), ZVEI Nameplate | 1.0, 2.0, 3.0 to 3.0.3, HSU variant | manufacturer, address |
| Digital Battery Passport – Digital Nameplate (IDTA 02035-1) | 1.0, 1.0.1 | manufacturer, address |
| Contact Information (IDTA 02002) | 1.0 to 1.0.4 | address |
| Hierarchical Structures enabling BoM (IDTA 02011) | 1.0, 1.1 to 1.1.4 | product tree |
| Technical Data (IDTA 02003) | ZVEI 1.0, 1.1, 1.2, 1.2.1, Generic Frame 2.0 to 2.0.4 | general information, classifications, properties with unit |
| Handover Documentation (IDTA 02004) | VDI 2770 1.0 (ZVEI), 1.2, 2.0 to 2.0.4 | documents, versions, files |
| Maintenance Instructions (IDTA 02018) | 1.0 to 1.0.2 | intervals, steps, tools, material, spare parts |

Patch versions (e.g. 1.0.1 → 1.0.3) cannot be distinguished in the files (same SemanticId and version
information) and are read together. IRDIs are compared without version suffix, value IRDIs (`0173-1#07-…`) are
translated into their text. Submodels without SemanticId are recognized by their idShort, empty template copies are
ignored.

Summary of the carbon footprint (`summary`): entries are only added up within the same calculation method, every
life cycle phase counts once (for overlaps such as A1-A3 next to A1, A2, A3 the finer split). The primary method is
ISO 14067, otherwise GHG Protocol, EN 15804, ISO 14040/14044, otherwise the first one stated; the others are listed
as alternatives in `methods`. Transports (TCF of 0.9) are counted as phase A4 and all added up.

Repeated elements are recognized independently of their spelling (`Document01`, `Document__00__`, `Document{00}`
or entries of a SubmodelElementList). Names, units and value lists come from the ConceptDescriptions of the loaded
files.

### AAS and AASX formats

AAS environments according to metamodel 3.0, 3.1 and 3.2 are read in XML and JSON, as well as AASX packages
according to IDTA-01005 3.0 to 3.2 (relationships with and without `www.`, `data.xml`/`data.json` and
`*.aas.xml`/`*.aas.json`). The tests read all valid examples (`maximal`/`minimal` of every class) of the latest
releases 3.0.9, 3.1.2 and 3.2.0 and check that XML and JSON give the same result and no attribute gets lost
(`tests/aas_format_examples.tar.gz`). New in 3.2 and only returned when present: `createdAt`/`updatedAt` in
`administration`; `DataSpecificationUom` appears as a content type of its own. AAS 2.0 (root element `aasenv`) is
not read.

The known template versions are listed in `src/carbon_footprint_api/submodels/known_templates.json`. New versions
on GitHub, including new releases of metamodel and AASX format, are found by `python tools/check_idta_templates.py`
in the project folder (see there).

### Handling of data errors

- AASX packages with broken relationships (e.g. a renamed `.aas.xml`) are loaded through the environment file that
  is present; damaged files are logged and skipped.
- Duplicate ZIP entries: the last one wins. Duplicate submodel ID within a shell: the duplicate is skipped.
- Elements without `idShort` are skipped when resolving paths.

## Estimates

`/products/{id}/estimates` estimates emissions for life cycle phases that no declared footprint covers. Declared
values are never changed or counted twice; every estimate states its formula, its inputs and their origin (shell,
product class, general assumption or set by the user) as well as the source of every factor.

| Phase | Estimate | Factor |
|---|---|---|
| A1-A3 production | mass × production factor of the material group; only without declared product footprint, otherwise a plausibility check (deviation above factor 3) | DESNZ "Material use" |
| A4 transport to the customer | mass × distance × factor of the means of transport; the distance is set by the user | DESNZ "Freighting goods" |
| B6 energy during use | power × operating hours per year × service life × electricity mix of the country | EEA, GHG emission intensity of electricity generation |
| C1-C4 end of life | mass × waste disposal factor of the material group (without credits for recycling) | DESNZ "Waste disposal" |

Mass, power and materials come from Technical Data (`/indicators`). Product class (ECLASS segment or ESPR product
category), service life, operating hours and material group per class are defined in
`src/carbon_footprint_api/estimates/classes.json`: service lives from the German depreciation table AfA-Tabelle AV
of the Federal Ministry of Finance, operating hours as a marked assumption (one or two shifts). Without a
recognized class, the median of the AfA table applies.

**Annual update of the factors** (DESNZ is published every June, EEA once a year):

1. Download the new editions into `factor-sources/`: DESNZ "Greenhouse gas reporting: conversion factors <year>",
   *flat file* (xlsx), from the
   [DESNZ page](https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting),
   and on the [EEA page](https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1-1783671782/greenhouse-gas-emission-intensity-of-electricity-generation)
   the chart data as CSV (file name `eea-electricity-….csv`). Remove older files.
2. `python tools/update_factors.py` writes `src/carbon_footprint_api/estimates/factors.json` and prints the
   factors taken over.
3. Run the tests, raise the API version (`patch`).

## Structure

```
src/carbon_footprint_api/
  aas/          Reading AAS XML/JSON/AASX into the response format, helpers
  submodels/    Version-dependent parsers of the IDTA templates, normalized models, summary, reference quantities
  estimates/    Estimates for phases without declared footprint, factors (factors.json) and class defaults
  repository/   Data storage: interface (AssetRepository) and in-memory implementation
  services/     Loading files from URLs (with SSRF protection and cache), uploads, product view
  api/          HTTP: routes, dependencies, error handling, middleware, static files
  config.py     Settings (command line and environment variables)
  main.py       Application factory create_app()
tests/          pytest, including snapshot comparison of all endpoints (snapshots.tar.gz), of all known
                IDTA templates (idta_templates.tar.gz) and format examples (aas_format_examples.tar.gz) from GitHub
tools/          record_snapshots.py to record the reference responses, update_factors.py for the emission factors
factor-sources/ Official source files of the emission factors (DESNZ, EEA)
```

## Security

- `/external-shells` only fetches public http(s) addresses (no localhost, no private or link-local networks, also
  not through redirects or DNS rebinding), with size and time limits. Downloaded shells never replace existing ones
  and are removed again following the LRU principle.
- `/uploads` accepts files up to `CFA_UPLOAD_MAX_MB` and stores them in `CFA_UPLOAD_DIR` (file name only from the
  random ID, never from the name given by the user), without a folder in memory only. Every upload gets a random,
  unguessable ID (144 bit); uploaded shells are hidden, never replace existing ones and are deleted after
  `CFA_UPLOAD_TTL_HOURS`, when `CFA_UPLOAD_MAX_COUNT` is exceeded and on every restart.
- AASX files are read with a size limit per entry (zip bombs), XML without entities and DTD (XXE).
- Attachments a browser could execute (HTML, SVG, XML, JavaScript) are only delivered as download with
  `Content-Security-Policy: sandbox`.
- Security headers (`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`), no `Server` header.
- CORS only for the API, only `GET` as well as `POST`/`DELETE` for uploads, without credentials. By default the
  server only binds to `127.0.0.1`.

## Development

```bash
pytest          # tests including snapshot comparison (needs ../repo)
ruff check      # linter including security rules
ruff format     # formatting
mypy            # type checking
pip-audit       # known vulnerabilities in dependencies
```

If the response format changes on purpose or files are added to or removed from `../repo`, record the reference
responses again (start the API on port 8080, then):

```bash
python tools/record_snapshots.py http://localhost:8080 snapshots /api/v4
tar czf tests/snapshots.tar.gz snapshots
```

## Versioning

Semantic versioning (`MAJOR.MINOR.PATCH`). The version is only stored in `src/carbon_footprint_api/__init__.py` and
is raised with every change by `python tools/bump_version.py api <major|minor|patch> "<description>"` (in the
project folder); the script also updates the changelogs. `MAJOR` rises with incompatible changes of the endpoints
and determines the prefix (`/api/v4`). A test checks that the newest changelog entry matches the version.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
