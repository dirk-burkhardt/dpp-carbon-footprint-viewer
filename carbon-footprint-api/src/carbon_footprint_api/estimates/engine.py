"""Estimates for life cycle phases without a declared footprint.

Rules (see docs/strategie-technical-data-und-hierarchie.md):

* Only phases that no declared footprint covers are estimated, so declared values are never counted twice.
* Every estimate states its formula, its inputs and where each input and factor comes from: the shell (Technical
  Data), the defaults of the product class (ECLASS or ESPR category), a general assumption or the request.
* Production (A1-A3) is only estimated if the shell declares no product footprint at all; otherwise the estimate is
  used as a plausibility check of the declared value.

Factors: DESNZ conversion factors (material production, waste disposal, freight) and EEA electricity intensity,
both republished every year and imported with ``tools/update_factors.py``. Service lives: AfA-Tabelle AV.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from ..submodels.models import (
    CarbonFootprintResult,
    Classification,
    Estimates,
    EstimateValue,
    Indicators,
    PhaseEstimate,
    Plausibility,
    ProductClassInfo,
    SourceInfo,
    TechnicalData,
)
from .data import all_sources, classes, factors

PRODUCTION_PHASES = ("A1", "A2", "A3")
END_OF_LIFE_PHASES = ("C1", "C2", "C3", "C4")
PLAUSIBLE_RANGE = (1 / 3, 3.0)


@dataclass
class EstimateParameters:
    """Assumptions the user may set; None means the default of the product class (or general default)."""

    country: str = "EU"
    lifetime_years: Optional[float] = None
    hours_per_year: Optional[float] = None
    transport_km: Optional[float] = None
    transport_mode: str = "road"


@dataclass
class _ClassDefaults:
    info: ProductClassInfo
    lifetime: Optional[dict[str, Any]]
    hours: Optional[dict[str, Any]]
    material: Optional[str]


def _eclass_digits(class_id: Optional[str]) -> str:
    return re.sub(r"\D", "", class_id or "")


def product_class(technical_data: list[TechnicalData]) -> _ClassDefaults:
    """Defaults of the first ECLASS class (by segment) or ESPR category found in Technical Data."""
    data = classes()
    found: list[Classification] = [c for td in technical_data for c in td.classifications]
    for c in found:
        if "eclass" not in (c.system or "").lower().replace("@", "").replace("-", ""):
            continue
        digits = _eclass_digits(c.classId)
        for entry in data["eclass"]:
            if digits.startswith(entry["prefix"]):
                info = ProductClassInfo(
                    system="ECLASS",
                    classId=c.classId,
                    label=entry["label"],
                    matchedBy=f"ECLASS {c.version or ''}".strip(),
                )
                return _ClassDefaults(info, entry["lifetime"], entry["hoursPerYear"], entry["material"])
    for c in found:
        entry = data["espr"].get((c.classId or "").strip().lower())
        if entry and "espr" in (c.system or "").lower():
            info = ProductClassInfo(system=c.system, classId=c.classId, label=entry["label"], matchedBy=c.system)
            return _ClassDefaults(info, entry["lifetime"], entry["hoursPerYear"], entry["material"])
    default = data["default"]
    first = found[0] if found else None
    info = ProductClassInfo(
        system=first.system if first else None,
        classId=first.classId if first else None,
        label=default["label"],
        matchedBy=None,
    )
    return _ClassDefaults(info, default["lifetime"], default["hoursPerYear"], default["material"])


def _material_from_indicators(indicators: Indicators) -> Optional[tuple[str, str]]:
    """Material group of the first material property that matches a keyword (housing first)."""
    keywords = classes()["materialKeywords"]
    ordered = sorted(
        indicators.materials, key=lambda m: 0 if "hous" in m.name.lower() or "gehäuse" in m.name.lower() else 1
    )
    for material in ordered:
        text = material.value.lower()
        for keyword in keywords:
            if re.search(keyword["pattern"], text):
                return keyword["material"], f"{material.name} = {material.value}"
    return None


def _value(name: str, value: float, unit: str, origin: str, source: Optional[str], reference: Optional[str]):
    return EstimateValue(name=name, value=value, unit=unit, origin=origin, source=source, reference=reference)  # type: ignore[arg-type]


def _covered(result: CarbonFootprintResult) -> set[str]:
    phases = set(result.summary.coveredPhases)
    for fp in result.footprints:
        if fp.kind == "product" and fp.co2eq is not None:
            phases.update(fp.lifeCyclePhases)
    return phases


def estimate(
    footprints: CarbonFootprintResult,
    indicators: Indicators,
    technical_data: list[TechnicalData],
    params: EstimateParameters,
) -> Estimates:
    data = factors()
    defaults = product_class(technical_data)
    result = Estimates(
        productClass=defaults.info,
        countries=list(data["electricity"]["countries"]),
        transportModes={k: v["label"] for k, v in data["freight"].items()},
    )
    covered = _covered(footprints)
    has_product = any(fp.kind == "product" and fp.co2eq is not None for fp in footprints.footprints)
    has_transport = any(fp.kind == "transport" and fp.co2eq is not None for fp in footprints.footprints)
    used_sources: set[str] = set()
    if any(fp.kind == "product" and fp.co2eq is not None and not fp.lifeCyclePhases for fp in footprints.footprints):
        result.warnings.append(
            "A declared product footprint does not state its life cycle phases. Estimated phases may already be "
            "included in it."
        )

    mass = None
    if indicators.mass:
        src = indicators.mass.source
        mass = _value(
            "mass", indicators.mass.value, "kg", "file", None, _describe(src.path, src.name or src.idShort, src.value)
        )

    # Material group: from the material properties of Technical Data, otherwise from the product class
    material_key: Optional[str] = None
    material_from_file = _material_from_indicators(indicators)
    if defaults.material and defaults.info.matchedBy:
        material_key = defaults.material
        material_origin, material_reference = "class", defaults.info.label
    elif material_from_file:
        material_key, material_reference = material_from_file
        material_origin = "file"
    material = data["materials"].get(material_key) if material_key else None
    if material is not None:
        result.material = _value(
            material["label"],
            material["productionKgCo2ePerKg"],
            "kg CO2e/kg",
            material_origin,
            None,
            material_reference,
        )

    # A1-A3: production from mass and material
    production_estimate: Optional[float] = None
    production_inputs: list[EstimateValue] = []
    if mass and material:
        production_estimate = mass.value * material["productionKgCo2ePerKg"]
        production_inputs = [
            mass,
            _value(
                f"production factor {material['label']}",
                material["productionKgCo2ePerKg"],
                "kg CO2e/kg",
                "factor",
                material["source"],
                material["productionReference"],
            ),
        ]
        used_sources.add(material["source"])
    if has_product:
        result.phases.append(
            PhaseEstimate(
                phase="A1-A3",
                label="production",
                status="declared",
                reason="covered by the declared product carbon footprint",
            )
        )
        declared = _declared_production(footprints)
        if production_estimate and declared:
            result.plausibility = _plausibility(declared, production_estimate)
    elif production_estimate is not None:
        result.phases.append(
            PhaseEstimate(
                phase="A1-A3",
                label="production",
                status="estimated",
                co2eq=production_estimate,
                formula="mass × production factor of the material group",
                inputs=production_inputs,
            )
        )
    else:
        result.phases.append(
            PhaseEstimate(
                phase="A1-A3",
                label="production",
                status="missing",
                reason=_missing(mass is None, "mass", material is None, "material or product class"),
            )
        )

    # A4: transport to the customer
    if "A4" in covered or has_transport:
        result.phases.append(
            PhaseEstimate(
                phase="A4",
                label="transport to final destination",
                status="declared",
                reason="covered by a declared transport or product carbon footprint",
            )
        )
    else:
        freight = data["freight"].get(params.transport_mode)
        if freight is None:
            result.warnings.append(f"Unknown transport mode {params.transport_mode}")
        if mass and freight and params.transport_km:
            distance = _value("distance", params.transport_km, "km", "user", None, None)
            factor = _value(
                f"freight factor {freight['label']}",
                freight["kgCo2ePerTonneKm"],
                "kg CO2e/t·km",
                "factor",
                freight["source"],
                freight["reference"],
            )
            used_sources.add(freight["source"])
            result.phases.append(
                PhaseEstimate(
                    phase="A4",
                    label="transport to final destination",
                    status="estimated",
                    co2eq=mass.value / 1000 * params.transport_km * freight["kgCo2ePerTonneKm"],
                    formula="mass in t × distance × freight factor",
                    inputs=[mass, distance, factor],
                )
            )
        else:
            result.phases.append(
                PhaseEstimate(
                    phase="A4",
                    label="transport to final destination",
                    status="missing",
                    reason=_missing(
                        mass is None, "mass", not params.transport_km, "transport distance (set it as assumption)"
                    ),
                )
            )

    # B6: energy consumption during use
    if "B6" in covered:
        result.phases.append(
            PhaseEstimate(
                phase="B6",
                label="usage energy consumption",
                status="declared",
                reason="covered by the declared product carbon footprint",
            )
        )
    else:
        result.phases.append(_usage_energy(indicators, defaults, params, data, used_sources))

    # C1-C4: end of life
    if covered.intersection(END_OF_LIFE_PHASES):
        result.phases.append(
            PhaseEstimate(
                phase="C1-C4",
                label="end of life",
                status="declared",
                reason="covered by the declared product carbon footprint",
            )
        )
    elif mass and material and material.get("endOfLifeKgCo2ePerKg") is not None:
        factor = _value(
            f"waste factor {material['label']} ({material['endOfLifeRoute']})",
            material["endOfLifeKgCo2ePerKg"],
            "kg CO2e/kg",
            "factor",
            material["source"],
            material["endOfLifeReference"],
        )
        used_sources.add(material["source"])
        result.phases.append(
            PhaseEstimate(
                phase="C1-C4",
                label="end of life",
                status="estimated",
                co2eq=mass.value * material["endOfLifeKgCo2ePerKg"],
                formula="mass × waste disposal factor (collection, transport and treatment, without recycling credits)",
                inputs=[mass, factor],
            )
        )
    else:
        result.phases.append(
            PhaseEstimate(
                phase="C1-C4",
                label="end of life",
                status="missing",
                reason=_missing(mass is None, "mass", material is None, "material or product class"),
            )
        )

    result.estimatedCo2eq = sum(p.co2eq or 0.0 for p in result.phases if p.status == "estimated")
    for value in [*(i for p in result.phases for i in p.inputs)]:
        if value.source:
            used_sources.add(value.source)
    sources = all_sources()
    result.sources = [SourceInfo(key=k, **_source_fields(sources[k])) for k in sorted(used_sources) if k in sources]
    return result


def _usage_energy(
    indicators: Indicators,
    defaults: _ClassDefaults,
    params: EstimateParameters,
    data: dict[str, Any],
    used_sources: set[str],
) -> PhaseEstimate:
    label = "usage energy consumption"
    if indicators.power is None:
        return PhaseEstimate(phase="B6", label=label, status="missing", reason="no power consumption in Technical Data")
    src = indicators.power.source
    power = _value(
        "power", indicators.power.value, "W", "file", None, _describe(src.path, src.name or src.idShort, src.value)
    )
    lifetime = _assumption(
        "service life", params.lifetime_years, defaults.lifetime, "years", "a", defaults, used_sources
    )
    hours = _assumption(
        "operating hours", params.hours_per_year, defaults.hours, "hours", "h/a", defaults, used_sources
    )
    if lifetime is None or hours is None:
        missing = "service life" if lifetime is None else "operating hours"
        return PhaseEstimate(
            phase="B6",
            label=label,
            status="missing",
            reason=f"no {missing} known for this product class (set it as assumption)",
        )
    countries = data["electricity"]["countries"]
    country = params.country.upper() if params.country.upper() in countries else "EU"
    grid = _value(
        f"electricity {country} {data['electricity']['year']}",
        countries[country],
        "kg CO2e/kWh",
        "factor",
        data["electricity"]["source"],
        "EU-27 average" if country == "EU" else f"country {country}",
    )
    used_sources.add(data["electricity"]["source"])
    energy_kwh = power.value * hours.value * lifetime.value / 1000
    return PhaseEstimate(
        phase="B6",
        label=label,
        status="estimated",
        co2eq=energy_kwh * grid.value,
        formula="power × operating hours per year × service life ÷ 1000 × electricity factor",
        inputs=[power, hours, lifetime, grid],
    )


def _assumption(
    name: str,
    requested: Optional[float],
    default: Optional[dict[str, Any]],
    key: str,
    unit: str,
    defaults: _ClassDefaults,
    used_sources: set[str],
) -> Optional[EstimateValue]:
    if requested is not None and requested > 0:
        return _value(name, requested, unit, "user", None, None)
    if not default:
        return None
    used_sources.add(default["source"])
    origin = "class" if defaults.info.matchedBy else "assumption"
    return _value(name, default[key], unit, origin, default["source"], default["reference"])


def _declared_production(result: CarbonFootprintResult) -> Optional[float]:
    """Declared product emissions of the primary method that cover only production phases."""
    method = result.summary.primaryMethod
    total = 0.0
    found = False
    for fp in result.footprints:
        if fp.kind != "product" or fp.co2eq is None or not fp.lifeCyclePhases:
            continue
        if method and ", ".join(fp.calculationMethods) not in (method, ""):
            continue
        if set(fp.lifeCyclePhases) <= set(PRODUCTION_PHASES):
            total += fp.co2eq
            found = True
    return total if found else None


def _plausibility(declared: float, estimated: float) -> Plausibility:
    ratio = declared / estimated if estimated > 0 else 0.0
    low, high = PLAUSIBLE_RANGE
    if ratio < low:
        assessment, note = (
            "low",
            "The declared production footprint is far below a typical value for this mass and material.",
        )
    elif ratio > high:
        assessment, note = (
            "high",
            "The declared production footprint is far above a typical value for this mass and material.",
        )
    else:
        assessment, note = "plausible", "The declared production footprint is in the range of a typical value."
    return Plausibility(
        declaredCo2eq=declared,
        estimatedCo2eq=estimated,
        ratio=ratio,
        assessment=assessment,  # type: ignore[arg-type]
        note=note + " The estimate uses average factors of a material group and is only a rough reference.",
    )


def _missing(*pairs: object) -> str:
    names = [str(pairs[i + 1]) for i in range(0, len(pairs), 2) if pairs[i]]
    return "missing: " + ", ".join(names) if names else "not possible"


def _describe(path: list[str], name: Optional[str], value: Optional[str]) -> str:
    return f"Technical Data: {' › '.join([*path, name or 'property'])} = {value}"


def _source_fields(source: dict[str, Any]) -> dict[str, Any]:
    fields = ("title", "publisher", "edition", "updated", "license", "url")
    return {k: (str(source[k]) if k == "edition" and source.get(k) is not None else source.get(k)) for k in fields}
