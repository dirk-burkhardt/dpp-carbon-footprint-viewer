"""Imports emission factors from the official source files into ``estimates/factors.json``.

The estimates of the API (``/products/{id}/estimates``) only use factors from trustworthy sources that publish a new
edition every year. Update once a year:

1. Download the new editions into ``factor-sources/`` (see README of the API, section "Schätzungen"):
   - DESNZ "Greenhouse gas reporting: conversion factors <year>", flat file (xlsx)
   - EEA "Greenhouse gas emission intensity of electricity generation, country level", chart data as CSV
2. ``python tools/update_factors.py`` (needs ``openpyxl``, part of the dev dependencies)
3. Check the printed factors, run the tests and raise the API version (patch).

Only the factors listed in ``SELECTION`` are taken over, each with its source, edition and row ID, so every value
shown in the user interface can be traced back to the publication.
"""

from __future__ import annotations

import csv
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "factor-sources"
TARGET = ROOT / "src" / "carbon_footprint_api" / "estimates" / "factors.json"

DESNZ_URL = "https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting"
EEA_URL = (
    "https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1-1783671782/"
    "greenhouse-gas-emission-intensity-of-electricity-generation"
)

# DESNZ rows: key -> (Level 1, Level 2, Level 3, Level 4, Column Text, UOM). All factors in kg CO2e.
FREIGHT = {
    "road": (
        "Freighting goods",
        "HGV (non-refrigerated, all diesel)",
        "Average non-refrigerated HGVs",
        None,
        "Average laden",
        "tonne.km",
    ),
    "van": ("Freighting goods", "Vans", "Average (up to 3.5 tonnes)", None, "Diesel", "tonne.km"),
    "rail": ("Freighting goods", "Rail", "Freight train", None, None, "tonne.km"),
    "sea": ("Freighting goods", "Cargo ship", "Container ship", "Average", None, "tonne.km"),
    "air": ("Freighting goods", "Freight flights", "International, to/from non-UK", None, "With RF", "tonne.km"),
}
FREIGHT_LABELS = {
    "road": "Truck (HGV, average load)",
    "van": "Van (up to 3.5 t)",
    "rail": "Freight train",
    "sea": "Container ship",
    "air": "Air freight (international, incl. radiative forcing)",
}

# Material groups: production factor (DESNZ "Material use", primary material production) and end-of-life factor
# (DESNZ "Waste disposal"). The DESNZ waste factors cover collection, transport and treatment of the waste only;
# credits for recycling are not included.
MATERIALS = {
    "electrical-small": ("Electrical items", "Electrical items - small", "WEEE - small", "Open-loop"),
    "electrical-large": ("Electrical items", "Electrical items - large", "WEEE - large", "Open-loop"),
    "electrical-it": ("Electrical items", "Electrical items - IT", "WEEE - mixed", "Open-loop"),
    "battery-li-ion": ("Electrical items", "Batteries - Li ion", "Batteries", "Open-loop"),
    "aluminium": ("Metal", "Metal: aluminium cans and foil (excl. forming)", None, "Closed-loop"),
    "steel": ("Metal", "Metal: steel cans", None, "Closed-loop"),
    "metal-mixed": ("Construction", "Metals", None, "Closed-loop"),
    "scrap-metal": ("Metal", "Metal: scrap metal", None, "Closed-loop"),
    "plastics": ("Plastic", "Plastics: average plastics", None, "Combustion"),
    "plastics-pp": ("Plastic", "Plastics: PP (incl. forming)", None, "Combustion"),
    "plastics-pvc": ("Plastic", "Plastics: PVC (incl. forming)", None, "Combustion"),
    "plastics-pet": ("Plastic", "Plastics: PET (incl. forming)", None, "Combustion"),
    "plastics-hdpe": ("Plastic", "Plastics: HDPE (incl. forming)", None, "Combustion"),
    "plastics-ps": ("Plastic", "Plastics: PS (incl. forming)", None, "Combustion"),
    "glass": ("Other", "Glass", None, "Closed-loop"),
    "paper": ("Paper", "Paper and board: mixed", None, "Closed-loop"),
    "wood": ("Construction", "Wood", None, "Combustion"),
    "textiles": ("Other", "Clothing", None, "Combustion"),
    "rubber": ("Construction", "Tyres", None, "Landfill"),
}

# EEA country names -> ISO 3166-1 alpha-2 (EU-27 as "EU")
COUNTRIES = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Ireland": "IE",
    "Italy": "IT",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Netherlands": "NL",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE",
    "EU-27": "EU",
}


def _desnz_file() -> Path:
    files = sorted(SOURCES.glob("ghg-conversion-factors-*flat*.xlsx"))
    if not files:
        raise SystemExit(f"Keine DESNZ-Datei (ghg-conversion-factors-<Jahr>-flat*.xlsx) in {SOURCES}")
    return files[-1]


def read_desnz(path: Path) -> tuple[int, dict[tuple, dict[str, Any]]]:
    import openpyxl  # only needed here, dev dependency

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Factors by Category"]
    rows = list(sheet.iter_rows(values_only=True))
    header_index = next(i for i, r in enumerate(rows) if r and "ID" in r and "Scope" in r)
    header = rows[header_index]
    columns = {name: i for i, name in enumerate(header) if name}
    factor_column = next(name for name in columns if str(name).startswith("GHG Conversion Factor"))
    year = int(re.search(r"(\d{4})", str(factor_column)).group(1))  # type: ignore[union-attr]
    table: dict[tuple, dict[str, Any]] = {}
    for row in rows[header_index + 1 :]:
        if not row or not row[columns["ID"]] or row[columns["GHG/Unit"]] != "kg CO2e":
            continue
        key = tuple(row[columns[c]] for c in ("Level 1", "Level 2", "Level 3", "Level 4", "Column Text", "UOM"))
        table[key] = {"id": row[columns["ID"]], "value": row[columns[factor_column]]}
    return year, table


def _desnz_value(table: dict, key: tuple, what: str) -> dict[str, Any]:
    entry = table.get(key)
    if entry is None or entry["value"] is None:
        raise SystemExit(f"DESNZ: Zeile für {what} nicht gefunden oder leer: {key}")
    return entry


def read_eea(path: Path) -> tuple[int, dict[str, float]]:
    """The chart CSV has a metadata block, then one line per country: values 1990..year, name, raw."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        lines = list(csv.reader(handle))
    header = next(line for line in lines if line and line[0] == "1990")
    years = [int(y) for y in header if y.isdigit()]
    latest = years[-1]
    values: dict[str, float] = {}
    for line in lines:
        if line is header or len(line) <= len(years) or not re.fullmatch(r"[\d.]+", line[0] or ""):
            continue
        name = re.sub(r"<[^>]+>", "", line[len(years)]).strip()
        code = COUNTRIES.get(name)
        if code is None:
            print(f"EEA: unbekanntes Land übersprungen: {name!r}", file=sys.stderr)
            continue
        raw = line[len(years) - 1]
        if raw:
            values[code] = round(float(raw) / 1000, 5)  # g/kWh -> kg/kWh
    if "EU" not in values or "DE" not in values:
        raise SystemExit("EEA: EU-27 oder Deutschland fehlt in der CSV-Datei")
    return latest, values


def main() -> None:
    desnz_path = _desnz_file()
    desnz_year, desnz = read_desnz(desnz_path)
    eea_files = sorted(SOURCES.glob("eea-electricity*.csv"))
    if not eea_files:
        raise SystemExit(f"Keine EEA-Datei (eea-electricity*.csv) in {SOURCES}")
    eea_year, electricity = read_eea(eea_files[-1])

    desnz_source = f"desnz-{desnz_year}"
    eea_source = f"eea-electricity-{eea_year}"
    freight = {}
    for mode, (l1, l2, l3, l4, text, uom) in FREIGHT.items():
        entry = _desnz_value(desnz, (l1, l2, l3, l4, text, uom), f"Transport {mode}")
        freight[mode] = {
            "label": FREIGHT_LABELS[mode],
            "kgCo2ePerTonneKm": entry["value"],
            "source": desnz_source,
            "reference": " › ".join(part for part in (l1, l2, l3, l4, text) if part) + f" (ID {entry['id']})",
        }
    materials = {}
    for key, (group, name, waste_name, route) in MATERIALS.items():
        production = _desnz_value(
            desnz, ("Material use", group, name, None, "Primary material production", "tonnes"), f"Material {key}"
        )
        waste_key = ("Waste disposal", group, waste_name or name, None, route, "tonnes")
        waste = desnz.get(waste_key)
        materials[key] = {
            "label": name,
            "productionKgCo2ePerKg": round(production["value"] / 1000, 6),
            "productionReference": (
                f"Material use › {group} › {name} › Primary material production (ID {production['id']})"
            ),
            "endOfLifeRoute": route,
            "endOfLifeKgCo2ePerKg": round(waste["value"] / 1000, 6) if waste and waste["value"] is not None else None,
            "endOfLifeReference": (
                f"Waste disposal › {group} › {waste_name or name} › {route} (ID {waste['id']})" if waste else None
            ),
            "source": desnz_source,
        }

    data = {
        "generated": datetime.date.today().isoformat(),
        "sources": {
            desnz_source: {
                "title": f"UK Government GHG Conversion Factors for Company Reporting {desnz_year}",
                "publisher": "Department for Energy Security and Net Zero (DESNZ)",
                "edition": desnz_year,
                "updated": "annually (June)",
                "license": "Open Government Licence v3.0",
                "url": DESNZ_URL,
                "file": desnz_path.name,
            },
            eea_source: {
                "title": "Greenhouse gas emission intensity of electricity generation, country level",
                "publisher": "European Environment Agency (EEA)",
                "edition": eea_year,
                "updated": "annually",
                "license": "CC BY 4.0",
                "url": EEA_URL,
                "file": eea_files[-1].name,
            },
        },
        "electricity": {
            "year": eea_year,
            "unit": "kg CO2e/kWh",
            "source": eea_source,
            "note": "GHG emission intensity of gross electricity generation; EU = average of EU-27",
            "countries": dict(sorted(electricity.items())),
        },
        "freight": freight,
        "materials": materials,
    }
    TARGET.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)} geschrieben: DESNZ {desnz_year}, EEA {eea_year}")
    for mode, f in freight.items():
        print(f"  Transport {mode}: {f['kgCo2ePerTonneKm']} kg CO2e/tkm")
    for key, m in materials.items():
        print(f"  Material {key}: {m['productionKgCo2ePerKg']} kg/kg, Entsorgung {m['endOfLifeKgCo2ePerKg']}")
    print(f"  Strom DE {electricity['DE']}, EU {electricity['EU']} kg/kWh")


if __name__ == "__main__":
    main()
