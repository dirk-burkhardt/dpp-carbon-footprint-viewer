# Strategy: Technical Data and Hierarchical Structures for the CO2 presentation

Status: 20 November 2026. All four stages are implemented (API 4.8.0, user interface 1.6.0); details on the
factors and their annual update are in the API README, section "Estimates".

## Starting point

The DPPviewer shows the **declared** emissions: product and transport carbon footprints from the Carbon Footprint
submodel, for assets with a bill of materials complemented by the footprints of the components. The API already
reads Technical Data and Hierarchical Structures (`/products/{id}/technical-data`, `/products/{id}/tree`), but the
user interface only used the hierarchy to build the component tree.

Neither submodel provides **additional emissions**; they provide two other things:

1. **Reference quantities** (mass, dimensions, power consumption, service life, material). With them, footprints
   of assets of different size become comparable, and gaps can be estimated.
2. **Structure** (components, quantities, depth). With it, one can show where the emissions come from and where
   data is missing.

## Principle: never mix declared and estimated values

Every value has an origin:

| Origin | Meaning | Presentation |
|---|---|---|
| declared | from a carbon footprint of the shell | as before, solid colour |
| from components | sum of the declared footprints of the components | as before |
| estimated | calculated from reference quantities and emission factors | hatched, with a reference to the assumptions |
| unknown | component or phase without data and without estimate | visible as a share of its own, not as zero |

Rules:

- Only life cycle phases that **no** declared footprint covers are estimated. The API already knows the covered
  phases (`summary.coveredPhases`). This avoids counting anything twice.
- The existing summation rule still applies: sums per calculation method across the phases, never across methods.
  Estimates form a "method" of their own.
- The declared totals in Overview, Compare and Datasheet stay unchanged. A total including estimates always
  appears separately and is labelled as such.

## 1. Technical Data

### 1a. Key figures per reference quantity (low risk, high benefit)

The API derives reference quantities with their unit from Technical Data and converts them into SI units (with the
ConceptDescriptions): mass in kg, power in W, volume in m³, service life in years. This results in intensities:

- CO2eq per kg (material and manufacturing efficiency)
- CO2eq per W of rated power (drives, power supplies, controllers)
- CO2eq per functional unit if the template provides it (e.g. kWh for batteries, already in the battery passport PCF)

Presentation: in the Overview as an additional key figure below the total, in Compare and Datasheet as a switchable
view "absolute / per kg / per W". If one of the assets lacks the reference quantity, the view marks this asset with
"no information" instead of guessing.

### 1b. Estimating missing phases

Only for phases the footprint does not cover. One simple, traceable formula per phase:

| Phase | Estimate | Required data |
|---|---|---|
| A1 to A3 (plausibility check if declared) | mass × material-specific factor | mass, material |
| A4 transport to the customer | mass × distance × factor per means of transport | mass, distance |
| B6 energy during use | power × operating hours per year × service life × electricity factor | power, service life, country |
| C1 to C4 end of life | mass × factor per material and disposal route | mass, material |

Assumptions the data does not provide (operating hours, service life, electricity mix, means of transport) are
preset, visible and can be changed by the user.

For A1 to A3, an estimate never replaces a declared value. It serves as plausibility check: if the declared value
is far outside the estimate, a notice appears.

## 2. Hierarchical Structures

The component tree exists. Without new data it allows the following evaluations:

- **Own manufacturing and purchased components:** footprint of the asset minus the sum of the component footprints
  (with quantities) gives the share of the own manufacturing. Shown as a bar in the Overview. The existing warning
  for a negative own share remains.
- **Data coverage:** share of the components with a footprint of their own, weighted with their quantity. Shown as
  key figure in the Overview and in the Datasheet.
- **Hotspots:** the components that together cause 80 % of the emissions. This shows where optimizing pays off and
  connects with the existing simulation (swapping a component).

## 3. Integration into the user interface

| View | Change |
|---|---|
| Overview | Intensities (per kg, per W), data coverage, own and purchased share; estimated, not declared emissions as hatched key figure. The total stays declared |
| Components | Hotspot table; switch between component analysis and simulation |
| Life Cycles | Declared and estimated emissions per phase, estimates hatched, with a switch to hide them |
| Estimates (after Life Cycles) | All estimates with formula, inputs (with path in the shell), factors with source and changeable assumptions. Changing an assumption updates Life Cycles and Overview |
| Compare, Datasheet | Switch absolute / per kg / per W (Compare), reference quantities and intensities (Datasheet) |

The view of its own matters because estimates without visible assumptions would look like facts. Life Cycles shows
the result, Estimates explains it.

## 4. Architecture

As for parsing, the calculation runs on the server; the user interface only presents:

- `GET /products/{id}/indicators`: reference quantities in SI units with source (submodel, path, original unit).
- `GET /products/{id}/estimates?country=…&lifetimeYears=…&hoursPerYear=…&transportKm=…&transportMode=…`:
  estimates per phase with formula, inputs and factors.
- Emission factors in a versioned file in the API package (`estimates/factors.json`) with source and edition per
  factor, imported every year from the official files by `tools/update_factors.py`. Only freely usable sources;
  commercial databases such as ecoinvent are excluded because of their license.

## 5. Stages

1. **Reference quantities and intensities** (API `indicators`, Overview, Compare, Datasheet). No assumptions needed.
2. **Evaluations of the hierarchy** (own and purchased share, data coverage, hotspots). No assumptions needed.
3. **Estimates B6 and A4** with the Estimates view and the extension of Life Cycles.
4. **Estimates C and plausibility check A1 to A3** (needs material information, which is maintained less often in
   the files).

## Decisions (18 November 2026)

- Factors only from trustworthy sources with an annual, citable edition: DESNZ conversion factors (material, waste
  disposal, transport) and EEA GHG emission intensity of electricity generation per country.
- Estimates are shown by default, hatched instead of solid, and can be hidden.
- Defaults per product class from the ECLASS classification in Technical Data (alternatively the ESPR category),
  stating the origin of every value. Service lives from the German depreciation table AfA-Tabelle AV (no annual
  edition), operating hours as a marked assumption.
- A4 is only estimated with a distance given by the user because the destination is missing in the data.
