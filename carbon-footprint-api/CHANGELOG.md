# Changelog

Changes of the Carbon Footprint API, newest version first. Versions follow [Semantic Versioning](https://semver.org/), see the [README](README.md#versioning).

## 4.9.0 – 2026-11-20

- Indicators: mass of cylinders and axes from basic weight, stroke and additional weight per stroke length (e.g. Festo DPDM); new field technicalDataFound and derivation of combined values
- Documentation (README, changelog) translated into English

## 4.8.0 – 2026-11-18

- New endpoint /products/{id}/estimates: estimates for life cycle phases without declared footprint (A1-A3 only without product footprint, otherwise a plausibility check; A4, B6, C1-C4) with formula, inputs and sources; factors from DESNZ 2026 and EEA 2024, service lives from the German depreciation table AfA-Tabelle AV, defaults per ECLASS segment or ESPR category
- Tool `tools/update_factors.py` takes the factors over from the official files in `factor-sources/` once a year (openpyxl as development dependency)
- Reference data of the tests recorded again for the current content of `repo`, test of the removed file "Stahlkugel" removed

## 4.7.0 – 2026-11-18

- New endpoint /products/{id}/indicators: reference quantities from Technical Data in SI units (mass, power, service life, dimensions, volume) with their source and material information

## 4.6.0 – 2026-11-18

- With CFA_UPLOAD_DIR uploads are stored in a folder (in the container repo/uploads, separate from the static files), attachments are read from the file; uploads of earlier runs are deleted there on startup, other files are left untouched; if the folder is not writable, uploads stay in memory
- Files loaded from links are discarded after `CFA_UPLOAD_TTL_HOURS` and loaded again on the next request
- Option `--uploadDir`

## 4.5.0 – 2026-11-18

- Temporary upload of AAS(X) files under `/uploads` (`POST`, `GET`, `DELETE`): in memory only, size limited by `CFA_UPLOAD_MAX_MB` (default 25 MB), deleted after `CFA_UPLOAD_TTL_HOURS` (default 3 h), with more than `CFA_UPLOAD_MAX_COUNT` uploads (default 20) and on every restart; random upload IDs, uploaded shells never replace existing ones
- Downloaded and uploaded shells share one bookkeeping, a shell is only removed when no source uses it any more
- CORS additionally allows `POST` and `DELETE` (for uploads)

## 4.4.0 – 2026-11-15

- Parsers for Technical Data (ZVEI 1.0 to Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 to 2.0.4) and Maintenance Instructions (1.0 to 1.0.2) with endpoints under /products; ConceptDescriptions of the files are read and provided under /concept-descriptions; AAS metamodel 3.2 (createdAt/updatedAt, DataSpecificationUom) and AASX fallback to data.xml/data.json
- Compatibility tests with all valid examples of the metamodel releases 3.0.9, 3.1.2 and 3.2.0 (XML and JSON) and the AASX examples 3.1/3.2
- The check script also reports new releases of aas-specs-metamodel and aas-specs-aasx

## 4.3.0 – 2026-11-15

- New endpoint /search: full-text search in all shells and submodels

## 4.2.0 – 2026-11-15

- Version-independent parsers for IDTA submodels: Carbon Footprint 0.9, 1.0 draft and 1.0 to 1.0.3 (metamodel 3.0/3.1) including the battery passport PCF, Digital Nameplate 1.0 to 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; detection of Handover Documentation and Technical Data
- New endpoints under `/api/v4/products`: detected templates per submodel, normalized carbon footprint with summary per calculation method, nameplate and product tree across all shells
- Value IRDIs from ECLASS value lists are translated into text; submodels without SemanticId are recognized by their idShort, empty template copies are ignored
- Tests against all known IDTA templates from GitHub (`tests/idta_templates.tar.gz`)

## 4.1.0 – 2026-11-15

- Operation as Docker container (python:3.13-slim, without root privileges, read-only file system, health check via /api/health) with docker-compose.yml; AASX files from repo are mounted to /opt/repo

## 4.0.0 – 2026-11-15

- Reimplemented in Python with FastAPI, replacing the former Java/Spring Boot implementation; response format unchanged so the user interface keeps working
- Incompatible: prefix `/api/v4` instead of `/api/v3.0`
- New: `/api/health`, configuration through environment variables `CFA_*`, options `--host`, `--logLevel`, `--noDocs`, `--noExternalShells`
- New: IDs are also accepted in standard Base64 (like `btoa` in the browser), also with `/` in the encoded value
- Security: SSRF protection and limits for `/external-shells`, downloads never overwrite existing shells, limited cache, size limit for AASX entries, safe delivery of active attachments, security headers, CORS only `GET` without credentials, default bind to `127.0.0.1`
- Fixed: elements without `idShort` caused HTTP 500; AASX with a broken relationship was not loaded; an unknown shell in submodel and attachment requests returns 404 instead of 500; `--aas` files were loaded twice; idShorts with `/` in the path
- Dependencies up to date, free licenses only (MIT, BSD, Apache-2.0, PSF)

## 0.0.1

- Original implementation in Java (Spring Boot, Eclipse AAS4J) with prefix `/api/v3.0`
