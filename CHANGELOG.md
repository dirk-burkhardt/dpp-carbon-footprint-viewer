# Changelog

Changelog of the whole project. Entries by date, each line names the part with its new version. The details are listed in the changelogs of the [API](carbon-footprint-api/CHANGELOG.md) and the [user interface](carbon-footprint-ui/CHANGELOG.md).

## 2026-11-22

- UI 1.8.1: Collapsed navigation of the single asset view: long labels such as "Components" break with a hyphen instead of reaching into the content

## 2026-11-20

- UI 1.8.0: Reduced view for small screens (below 768 px): compact header, asset list without favourites column, compact single asset view with totals, key figures, emissions per phase and estimates; Compare, Datasheet and the analyses of the single view show a notice and can be opened anyway
- UI 1.7.0: Search on the asset selection keeps the tabs: their counts show the matches, the open tab lists only its own matches
- UI 1.7.0: Single asset view: Estimates moved below Life Cycles; the navigation on the left has a fixed width, so the separator no longer moves between the views
- UI 1.7.0: Simulation removed from the navigation; on Components a switch below the component counts changes between component analysis and simulation (disabled without components); breadcrumb Overview > Component Analysis > Simulation
- UI 1.7.0: Overview: key figures per kg and per W name the reason if a reference quantity is missing (no Technical Data submodel or not stated in it) and show calculated masses with their derivation
- UI 1.7.0: Documentation (README, changelogs) translated into English
- API 4.9.0: Documentation (README, changelog) translated into English
- Project README, changelog, `docs/strategy-technical-data-and-hierarchy.md`, `.env.example` and comments in `docker-compose.yml` translated into English; documentation is maintained in English from now on
- API 4.9.0: Indicators: mass of cylinders and axes from basic weight, stroke and additional weight per stroke length (e.g. Festo DPDM); new field technicalDataFound and derivation of combined values

## 2026-11-18

- API 4.8.0: New endpoint /products/{id}/estimates: estimates for life cycle phases without declared footprint (A1-A3 only without product footprint, otherwise a plausibility check; A4, B6, C1-C4) with formula, inputs and sources; factors from DESNZ 2026 and EEA 2024, service lives from the German depreciation table AfA-Tabelle AV, defaults per ECLASS segment or ESPR category
- API 4.8.0: Tool `tools/update_factors.py` takes the factors over from the official files in `factor-sources/` once a year (openpyxl as development dependency)
- API 4.8.0: Reference data of the tests recorded again for the current content of `repo`, test of the removed file "Stahlkugel" removed
- API 4.7.0: New endpoint /products/{id}/indicators: reference quantities from Technical Data in SI units (mass, power, service life, dimensions, volume) with their source and material information
- API 4.6.0: With CFA_UPLOAD_DIR uploads are stored in a folder (in the container repo/uploads, separate from the static files), attachments are read from the file; uploads of earlier runs are deleted there on startup, other files are left untouched; if the folder is not writable, uploads stay in memory
- API 4.6.0: Files loaded from links are discarded after `CFA_UPLOAD_TTL_HOURS` and loaded again on the next request
- API 4.6.0: Option `--uploadDir`
- API 4.5.0: Temporary upload of AAS(X) files under `/uploads` (`POST`, `GET`, `DELETE`): in memory only, size limited by `CFA_UPLOAD_MAX_MB` (default 25 MB), deleted after `CFA_UPLOAD_TTL_HOURS` (default 3 h), with more than `CFA_UPLOAD_MAX_COUNT` uploads (default 20) and on every restart; random upload IDs, uploaded shells never replace existing ones
- API 4.5.0: Downloaded and uploaded shells share one bookkeeping, a shell is only removed when no source uses it any more
- API 4.5.0: CORS additionally allows `POST` and `DELETE` (for uploads)
- UI 1.6.0: New Estimates view (after Components) with assumptions, formulas, inputs and sources; estimates hatched in Overview and Life Cycles, shown by default and can be hidden
- UI 1.6.0: Life Cycles: new chart "Declared and Estimated Emissions per Phase", declared values solid, estimated values hatched
- UI 1.6.0: Overview: key figures also for assets without carbon footprint (e.g. estimated production)
- UI 1.5.0: Key figures in the Overview: CO2eq per kg and per W (from Technical Data), share of own manufacturing and data coverage of the components
- UI 1.5.0: Components: table "Hotspots" with the components that together cause 80 % of the declared emissions (per component its own share for all units)
- UI 1.5.0: Compare: switch "Absolute / per kg / per W", disabled if an asset lacks the information
- UI 1.5.0: Datasheet: rows mass, power, CO2eq per kg and per W, own manufacturing and data coverage
- UI 1.5.0: Breadcrumb "Asset Selection" opens the tab shown last again (e.g. External assets)
- UI 1.4.0: Files loaded from links and uploaded files stay listed in the browser under External assets, also after switching to the overview or reloading, until they expire with the time of the server or are removed
- UI 1.4.0: Carbon footprints come from the normalized endpoint of the API (`/products/{id}/carbon-footprint`) instead of an own evaluation of the submodels; this shows all versions of the template (so far only the structure of 0.9, footprints according to 1.0 appeared as "carbon footprint provided" but without values). Without this endpoint (third-party AAS server) the submodels are evaluated as before; warnings of the API appear with asset and element in the problem table
- UI 1.3.0: Upload AAS(X) files under "External assets"; size and retention come from the API, removing an upload also deletes it on the server, links work until it expires
- UI 1.3.0: Tabs "Pre-loaded assets" and "External assets" designed more clearly as tabs (active tab with coloured top edge, connected with the content, number of assets), in light and dark mode
- UI 1.3.0: The header with the search only stays in view on the asset selection, in the analyses it scrolls away; navigation and simulation notice then stick to the top of the window
- UI 1.3.0: Breadcrumbs: "Overview of One Asset" is now called "Overview", the simulation "Simulation" instead of "Component Analysis"
- UI 1.3.0: Problem table: column "Asset" with the affected assets, expanded every occurrence (asset and element); equal warnings are only counted once per asset and element, loading again no longer raises the count
- UI 1.3.0: Compare: switch "Opposed bars" / "Bars side by side" shows both bars of a row next to each other in one chart
- UI 1.3.0: Fixed the error "can't access property startsWith, t is undefined" that occurred when leaving an analysis (e.g. through the breadcrumbs)
- UI 1.3.0: nginx in the container: uploads up to `UPLOAD_MAX_MB` (+1 MB) through `/api/v4/uploads`, at most 10 uploads per minute and client
- Changelogs moved from the READMEs into files of their own `CHANGELOG.md` (project, API, user interface); `tools/bump_version.py`, the API test and the version check of the user interface read from there
- README: section "Quick start (Docker, local)" with settings and all addresses in the browser; README of the user interface: outdated Docker section replaced
- Concept `docs/strategy-technical-data-and-hierarchy.md`: use of Technical Data and Hierarchical Structures for the CO2 presentation, extended by the decisions
- `docker-compose.yml`: `repo/uploads` as the only writable folder of the API container
- `CLAUDE.md`: follow the rules in `AI_Coding` and check them for changes now and then; annual update of the emission factors

## 2026-11-15

- API 4.4.0: Parsers for Technical Data (ZVEI 1.0 to Generic Frame 2.0.4), Handover Documentation (VDI 2770 1.0, 1.2, 2.0 to 2.0.4) and Maintenance Instructions (1.0 to 1.0.2) with endpoints under /products; ConceptDescriptions of the files are read and provided under /concept-descriptions; AAS metamodel 3.2 (createdAt/updatedAt, DataSpecificationUom) and AASX fallback to data.xml/data.json
- API 4.4.0: Compatibility tests with all valid examples of the metamodel releases 3.0.9, 3.1.2 and 3.2.0 (XML and JSON) and the AASX examples 3.1/3.2
- API 4.4.0: The check script also reports new releases of aas-specs-metamodel and aas-specs-aasx
- API 4.3.0: New endpoint /search: full-text search in all shells and submodels
- API 4.2.0: Version-independent parsers for IDTA submodels: Carbon Footprint 0.9, 1.0 draft and 1.0 to 1.0.3 (metamodel 3.0/3.1) including the battery passport PCF, Digital Nameplate 1.0 to 3.0.3, Contact Information, Hierarchical Structures 1.0/1.1; detection of Handover Documentation and Technical Data
- API 4.2.0: New endpoints under `/api/v4/products`: detected templates per submodel, normalized carbon footprint with summary per calculation method, nameplate and product tree across all shells
- API 4.2.0: Value IRDIs from ECLASS value lists are translated into text; submodels without SemanticId are recognized by their idShort, empty template copies are ignored
- API 4.2.0: Tests against all known IDTA templates from GitHub (`tests/idta_templates.tar.gz`)
- API 4.1.0: Operation as Docker container (python:3.13-slim, without root privileges, read-only file system, health check via /api/health) with docker-compose.yml; AASX files from repo are mounted to /opt/repo
- API 4.0.0: Reimplemented in Python with FastAPI, replacing the former Java/Spring Boot implementation; response format unchanged so the user interface keeps working
- API 4.0.0: Incompatible: prefix `/api/v4` instead of `/api/v3.0`
- API 4.0.0: New: `/api/health`, configuration through environment variables `CFA_*`, options `--host`, `--logLevel`, `--noDocs`, `--noExternalShells`
- API 4.0.0: New: IDs are also accepted in standard Base64 (like `btoa` in the browser), also with `/` in the encoded value
- API 4.0.0: Security: SSRF protection and limits for `/external-shells`, downloads never overwrite existing shells, limited cache, size limit for AASX entries, safe delivery of active attachments, security headers, CORS only `GET` without credentials, default bind to `127.0.0.1`
- API 4.0.0: Fixed: elements without `idShort` caused HTTP 500; AASX with a broken relationship was not loaded; an unknown shell in submodel and attachment requests returns 404 instead of 500; `--aas` files were loaded twice; idShorts with `/` in the path
- API 4.0.0: Dependencies up to date, free licenses only (MIT, BSD, Apache-2.0, PSF)
- UI 1.2.5: Logo in the header with the lettering "DPPviewer" instead of "CLiCE - DiPP" (file src/assets/DPPviewer-logo.svg, font Quicksand as path)
- UI 1.2.4: Favicon and app icons show the CLiCE-DiPP logo (magnifying glass with leaf label)
- UI 1.2.4: Datasheet: long asset names in the header are shortened, the full name appears on hover
- UI 1.2.3: Datasheet scrolls horizontally with many assets, the left column with the labels stays in place
- UI 1.2.2: Datasheet shows all favourites, also without CO2 data (cells with "no data"); an asset that cannot be loaded no longer blocks the whole datasheet
- UI 1.2.2: Favourites box: Compare and Datasheet with icons, separated from the title by lines; favourites in an area of their own with a lighter background
- UI 1.2.2: Status icon on the start page at the bottom right instead of centred below the favourites
- UI 1.2.2: Problem table by default about a third of the window height, more compact rows, scrolling without scrolling the page
- UI 1.2.1: The map of the overview no longer slides over the header when scrolling
- UI 1.2.1: Duplicate selection "More" (Components, Life Cycles, Simulation) with icon below the single asset view removed, the navigation on the left is sufficient
- UI 1.2.1: Dark mode: labels and lines of the charts in Overview, Components, Life Cycles and Simulation in the text colour of the theme instead of black; address field on the map easier to read
- UI 1.2.1: Problem table higher (45 % of the window height), height adjustable at the top edge, larger font
- UI 1.2.1: Deviating calculations (CO2eq of the components higher than that of the asset, missing information Well-to-Tank/Tank-to-Wheel) appear as warning instead of error
- UI 1.2.0: New design: header with logo, search (optionally within the shells), light/dark and info; the left column is gone
- UI 1.2.0: Favourites can be sorted by drag and drop, the favourites box offers the analyses Compare (the first two favourites) and Datasheet (all favourites); existing favourites are kept
- UI 1.2.0: Compare as graphical comparison of two assets following the concept of the thesis (bars in two directions around a zero line, absolute values or difference, transport and product per life cycle phase)
- UI 1.2.0: Datasheet without adding shells of its own, more compact layout; sum of the life cycle phases from components corrected (quantities were partly counted twice or not at all)
- UI 1.2.0: A click on a shell opens the single asset view, the selection buttons on hover are gone; yellow frame only for favourites
- UI 1.2.0: Status icon (OK, warnings, errors with count) below the favourites, on other pages at the bottom right; a click opens a compact table, equal messages are combined
- UI 1.2.0: Global error message at the top removed: loading errors only appear in the affected view, also if the request fails after a page change
- UI 1.1.0: Operation as Docker container with nginx: forwarding of /api to the API, runtime configuration and Content Security Policy from environment variables, security headers, caching, limit for downloads from URLs; address search can be disabled with GEOCODING_URL=off
- UI 1.0.0: Renamed from `carbon-trace` to `carbon-footprint-ui`, the logo at the top left is now the CLiCE-DiPP logo
- UI 1.0.0: Incompatible: uses the API 4.x under `/api/v4`; in development Vite forwards `/api` to the API
- UI 1.0.0: Maps with Leaflet and OpenStreetMap, address search through Nominatim instead of Mapbox (no commercial license and no access token needed any more)
- UI 1.0.0: Version display of user interface and API on the About page
- UI 1.0.0: Updated: Vue 3.5, vue-router 5, Vite 8, Tailwind CSS 4, daisyUI 5, TypeScript 6, ESLint 10; unused packages removed (ECharts, pako, htl)
- UI 1.0.0: Fixed: transport footprints were discarded in the simulation; wrong tooltips in the change chart with an active filter; breadcrumbs of the two-asset view; IDs with umlauts and special characters; failed requests were kept until reloading; detection of the dark mode; names in bold in tooltips; simulation link
- UI 1.0.0: Security: attachment paths are encoded, external links with `noopener`, no credentials in the code, `npm audit` without findings
- UI 1.0.0: Views are only loaded when needed (initial bundle 378 instead of 995 KB), type check and lint without errors
- Check script `tools/check_idta_templates.py` for new versions of the IDTA submodel templates on GitHub; note in `CLAUDE.md` to run it at the start of every work session
- Project cleaned up: Java implementation of the API and old frontend folder `carbon-trace-main` removed, versioning and changelogs introduced
