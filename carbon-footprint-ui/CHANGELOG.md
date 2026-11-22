# Changelog

Changes of the DPPviewer user interface, newest version first. Versions follow [Semantic Versioning](https://semver.org/), see the [README](README.md#versioning).

## 1.8.1 – 2026-11-22

- Collapsed navigation of the single asset view: long labels such as "Components" break with a hyphen instead of reaching into the content

## 1.8.0 – 2026-11-20

- Reduced view for small screens (below 768 px): compact header, asset list without favourites column, compact single asset view with totals, key figures, emissions per phase and estimates; Compare, Datasheet and the analyses of the single view show a notice and can be opened anyway

## 1.7.0 – 2026-11-20

- Search on the asset selection keeps the tabs: their counts show the matches, the open tab lists only its own matches
- Single asset view: Estimates moved below Life Cycles; the navigation on the left has a fixed width, so the separator no longer moves between the views
- Simulation removed from the navigation; on Components a switch below the component counts changes between component analysis and simulation (disabled without components); breadcrumb Overview > Component Analysis > Simulation
- Overview: key figures per kg and per W name the reason if a reference quantity is missing (no Technical Data submodel or not stated in it) and show calculated masses with their derivation
- Documentation (README, changelogs) translated into English

## 1.6.0 – 2026-11-18

- New Estimates view (after Components) with assumptions, formulas, inputs and sources; estimates hatched in Overview and Life Cycles, shown by default and can be hidden
- Life Cycles: new chart "Declared and Estimated Emissions per Phase", declared values solid, estimated values hatched
- Overview: key figures also for assets without carbon footprint (e.g. estimated production)

## 1.5.0 – 2026-11-18

- Key figures in the Overview: CO2eq per kg and per W (from Technical Data), share of own manufacturing and data coverage of the components
- Components: table "Hotspots" with the components that together cause 80 % of the declared emissions (per component its own share for all units)
- Compare: switch "Absolute / per kg / per W", disabled if an asset lacks the information
- Datasheet: rows mass, power, CO2eq per kg and per W, own manufacturing and data coverage
- Breadcrumb "Asset Selection" opens the tab shown last again (e.g. External assets)

## 1.4.0 – 2026-11-18

- Files loaded from links and uploaded files stay listed in the browser under External assets, also after switching to the overview or reloading, until they expire with the time of the server or are removed
- Carbon footprints come from the normalized endpoint of the API (`/products/{id}/carbon-footprint`) instead of an own evaluation of the submodels; this shows all versions of the template (so far only the structure of 0.9, footprints according to 1.0 appeared as "carbon footprint provided" but without values). Without this endpoint (third-party AAS server) the submodels are evaluated as before; warnings of the API appear with asset and element in the problem table

## 1.3.0 – 2026-11-18

- Upload AAS(X) files under "External assets"; size and retention come from the API, removing an upload also deletes it on the server, links work until it expires
- Tabs "Pre-loaded assets" and "External assets" designed more clearly as tabs (active tab with coloured top edge, connected with the content, number of assets), in light and dark mode
- The header with the search only stays in view on the asset selection, in the analyses it scrolls away; navigation and simulation notice then stick to the top of the window
- Breadcrumbs: "Overview of One Asset" is now called "Overview", the simulation "Simulation" instead of "Component Analysis"
- Problem table: column "Asset" with the affected assets, expanded every occurrence (asset and element); equal warnings are only counted once per asset and element, loading again no longer raises the count
- Compare: switch "Opposed bars" / "Bars side by side" shows both bars of a row next to each other in one chart
- Fixed the error "can't access property startsWith, t is undefined" that occurred when leaving an analysis (e.g. through the breadcrumbs)
- nginx in the container: uploads up to `UPLOAD_MAX_MB` (+1 MB) through `/api/v4/uploads`, at most 10 uploads per minute and client

## 1.2.5 – 2026-11-15

- Logo in the header with the lettering "DPPviewer" instead of "CLiCE - DiPP" (file src/assets/DPPviewer-logo.svg, font Quicksand as path)

## 1.2.4 – 2026-11-15

- Favicon and app icons show the CLiCE-DiPP logo (magnifying glass with leaf label)
- Datasheet: long asset names in the header are shortened, the full name appears on hover

## 1.2.3 – 2026-11-15

- Datasheet scrolls horizontally with many assets, the left column with the labels stays in place

## 1.2.2 – 2026-11-15

- Datasheet shows all favourites, also without CO2 data (cells with "no data"); an asset that cannot be loaded no longer blocks the whole datasheet
- Favourites box: Compare and Datasheet with icons, separated from the title by lines; favourites in an area of their own with a lighter background
- Status icon on the start page at the bottom right instead of centred below the favourites
- Problem table by default about a third of the window height, more compact rows, scrolling without scrolling the page

## 1.2.1 – 2026-11-15

- The map of the overview no longer slides over the header when scrolling
- Duplicate selection "More" (Components, Life Cycles, Simulation) with icon below the single asset view removed, the navigation on the left is sufficient
- Dark mode: labels and lines of the charts in Overview, Components, Life Cycles and Simulation in the text colour of the theme instead of black; address field on the map easier to read
- Problem table higher (45 % of the window height), height adjustable at the top edge, larger font
- Deviating calculations (CO2eq of the components higher than that of the asset, missing information Well-to-Tank/Tank-to-Wheel) appear as warning instead of error

## 1.2.0 – 2026-11-15

- New design: header with logo, search (optionally within the shells), light/dark and info; the left column is gone
- Favourites can be sorted by drag and drop, the favourites box offers the analyses Compare (the first two favourites) and Datasheet (all favourites); existing favourites are kept
- Compare as graphical comparison of two assets following the concept of the thesis (bars in two directions around a zero line, absolute values or difference, transport and product per life cycle phase)
- Datasheet without adding shells of its own, more compact layout; sum of the life cycle phases from components corrected (quantities were partly counted twice or not at all)
- A click on a shell opens the single asset view, the selection buttons on hover are gone; yellow frame only for favourites
- Status icon (OK, warnings, errors with count) below the favourites, on other pages at the bottom right; a click opens a compact table, equal messages are combined
- Global error message at the top removed: loading errors only appear in the affected view, also if the request fails after a page change

## 1.1.0 – 2026-11-15

- Operation as Docker container with nginx: forwarding of /api to the API, runtime configuration and Content Security Policy from environment variables, security headers, caching, limit for downloads from URLs; address search can be disabled with GEOCODING_URL=off

## 1.0.0 – 2026-11-15

- Renamed from `carbon-trace` to `carbon-footprint-ui`, the logo at the top left is now the CLiCE-DiPP logo
- Incompatible: uses the API 4.x under `/api/v4`; in development Vite forwards `/api` to the API
- Maps with Leaflet and OpenStreetMap, address search through Nominatim instead of Mapbox (no commercial license and no access token needed any more)
- Version display of user interface and API on the About page
- Updated: Vue 3.5, vue-router 5, Vite 8, Tailwind CSS 4, daisyUI 5, TypeScript 6, ESLint 10; unused packages removed (ECharts, pako, htl)
- Fixed: transport footprints were discarded in the simulation; wrong tooltips in the change chart with an active filter; breadcrumbs of the two-asset view; IDs with umlauts and special characters; failed requests were kept until reloading; detection of the dark mode; names in bold in tooltips; simulation link
- Security: attachment paths are encoded, external links with `noopener`, no credentials in the code, `npm audit` without findings
- Views are only loaded when needed (initial bundle 378 instead of 995 KB), type check and lint without errors

## 0.0.0

- Original user interface `carbon-trace` (Vue 3, Vite 5, Tailwind CSS 3, Mapbox)
