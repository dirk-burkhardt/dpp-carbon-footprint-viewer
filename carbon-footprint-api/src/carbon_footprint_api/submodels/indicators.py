"""Reference quantities (mass, power, service life, dimensions, materials) from Technical Data.

Manufacturers fill Technical Data very differently: with ECLASS or ETIM semantic ids and a unit in the
ConceptDescription, or only with an idShort such as ``Product_weight`` and the unit in the value (``"2,250 g"``).
The rules below therefore combine known semantic ids, normalized names and units, and only accept a value whose
unit fits the quantity (``"8 A"`` is no power). Values are converted to SI units.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Optional

from .models import Indicators, MaterialInfo, Measure, MeasureSource, TechnicalData, TechnicalProperty

# Factors to the SI unit of each kind of quantity; keys are lower case
_UNITS: dict[str, dict[str, float]] = {
    "mass": {
        "mg": 1e-6,
        "g": 1e-3,
        "gram": 1e-3,
        "grams": 1e-3,
        "kg": 1.0,
        "kilogram": 1.0,
        "t": 1000.0,
        "lb": 0.45359237,
        "lbs": 0.45359237,
        "oz": 0.028349523125,
    },
    "power": {"mw": 1e-3, "milliwatt": 1e-3, "w": 1.0, "watt": 1.0, "kw": 1e3, "kilowatt": 1e3, "mw_": 1e6},
    "length": {"mm": 1e-3, "cm": 1e-2, "dm": 1e-1, "m": 1.0, "in": 0.0254, "inch": 0.0254},
    "time": {
        "a": 1.0,
        "y": 1.0,
        "yr": 1.0,
        "year": 1.0,
        "years": 1.0,
        "jahr": 1.0,
        "jahre": 1.0,
        "month": 1 / 12,
        "months": 1 / 12,
        "monate": 1 / 12,
        "d": 1 / 365,
        "day": 1 / 365,
        "days": 1 / 365,
        "h": 1 / 8760,
        "hour": 1 / 8760,
        "hours": 1 / 8760,
        "std": 1 / 8760,
    },
}
_SI_UNIT = {"mass": "kg", "power": "W", "length": "m", "time": "a"}

# Semantic ids that identify a quantity regardless of its name (version suffix ignored)
_SEMANTIC_IDS = {
    "mass": ("0173-1#02-BAD875",),  # ECLASS net weight
}

# Names after normalization (lower case, words separated by single spaces, unit suffix removed)
_NAMES = {
    "mass": {
        "product weight",
        "net weight",
        "weight",
        "nettogewicht",
        "gewicht",
        "produktgewicht",
        "mass",
        "masse",
        "net mass",
        "total weight",
        "gesamtgewicht",
        "weight of product",
    },
    "power": {
        "power consumption",
        "power input",
        "power input ul",
        "rated power",
        "nominal power",
        "leistungsaufnahme",
        "nennleistung",
        "electrical power",
        "power",
        "max power consumption",
        "typical power consumption",
        "leistung",
        "elektrische leistung",
    },
    "lifetime": {
        "service life",
        "lifetime",
        "life time",
        "expected lifetime",
        "lebensdauer",
        "nutzungsdauer",
        "expected service life",
        "useful life",
    },
    "width": {"width", "breite"},
    "height": {"height", "höhe", "hoehe"},
    "depth": {"depth", "tiefe"},
}
_KIND = {"mass": "mass", "power": "power", "lifetime": "time", "width": "length", "height": "length", "depth": "length"}

_NUMBER = re.compile(r"^\s*([-+]?\d[\d.,]*)\s*([^\d\s].*)?$")
_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")


def normalize_name(name: Optional[str]) -> str:
    """``Product_weight`` -> ``product weight``, ``heightMm`` -> ``height mm``."""
    if not name:
        return ""
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = re.sub(r"[_\-./]+", " ", name)
    return " ".join(name.lower().split())


def parse_number(raw: str) -> Optional[float]:
    """Parses ``2,250`` (thousands separator), ``0,5`` (decimal comma) and ``1.5``."""
    raw = raw.strip()
    if _THOUSANDS.match(raw):
        raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:
        raw = raw.replace(",", ".")
    elif "," in raw and "." in raw:
        # 1.234,5 (German) or 1,234.5 (English): the last separator is the decimal point
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _value_and_unit(prop: TechnicalProperty, name_unit: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    if prop.modelType != "Property" or not prop.value:
        return None, None
    match = _NUMBER.match(prop.value)
    if not match:
        return None, None
    number = parse_number(match.group(1))
    unit = prop.unit or (match.group(2) or "").strip() or name_unit
    return number, unit


def _factor(kind: str, unit: Optional[str]) -> Optional[float]:
    if not unit:
        return None
    key = unit.strip().lower().rstrip(".")
    if kind == "power" and unit.strip() == "MW":
        key = "mw_"
    return _UNITS[kind].get(key)


def _split_unit_suffix(name: str, kind: str) -> tuple[str, Optional[str]]:
    """``height mm`` -> (``height``, ``mm``); ETIM idShorts often end with the unit."""
    words = name.split(" ")
    if len(words) > 1 and words[-1] in _UNITS[kind]:
        return " ".join(words[:-1]), words[-1]
    return name, None


def _source(td: TechnicalData, prop: TechnicalProperty, unit: Optional[str]) -> MeasureSource:
    return MeasureSource(
        submodelId=td.submodelId,
        path=prop.path,
        idShort=prop.idShort,
        name=prop.name,
        semanticId=prop.semanticId,
        value=prop.value,
        unit=unit,
    )


def _candidates(technical_data: Iterable[TechnicalData]) -> Iterable[tuple[TechnicalData, TechnicalProperty]]:
    for td in technical_data:
        for area in [*td.areas, *td.specificDescriptions]:
            for prop in area.properties:
                yield td, prop


def _match(quantity: str, prop: TechnicalProperty) -> tuple[int, Optional[str]] | None:
    """Priority of a property for a quantity (lower is better) and the unit taken from its name."""
    kind = _KIND[quantity]
    sid = prop.semanticId or ""
    if any(sid.startswith(known) for known in _SEMANTIC_IDS.get(quantity, ())):
        return 0, None
    for priority, raw in ((1, prop.idShort), (2, prop.name)):
        name, unit = _split_unit_suffix(normalize_name(raw), kind)
        if name in _NAMES[quantity]:
            return priority, unit
    return None


def derive_indicators(technical_data: list[TechnicalData]) -> Indicators:
    result = Indicators()
    for quantity, kind in _KIND.items():
        found: list[tuple[int, Measure]] = []
        for td, prop in _candidates(technical_data):
            matched = _match(quantity, prop)
            if matched is None:
                continue
            number, unit = _value_and_unit(prop, matched[1])
            factor = _factor(kind, unit)
            if number is None or factor is None or number < 0:
                continue
            measure = Measure(value=number * factor, unit=_SI_UNIT[kind], source=_source(td, prop, unit))
            found.append((matched[0], measure))
        if not found:
            continue
        found.sort(key=lambda item: item[0])
        best = found[0][1]
        setattr(result, quantity, best)
        others = {round(m.value, 9) for _, m in found[1:]} - {round(best.value, 9)}
        if others:
            result.warnings.append(
                f"Mehrere Angaben für {quantity}: verwendet {best.source.idShort} ({best.source.value})"
            )
    if result.width and result.height and result.depth:
        result.volume = result.width.value * result.height.value * result.depth.value
    for td, prop in _candidates(technical_data):
        name = normalize_name(prop.idShort or prop.name)
        if name.startswith("material") and "note" not in name and prop.value and prop.modelType != "File":
            result.materials.append(
                MaterialInfo(
                    name=prop.name or prop.idShort or "Material", value=prop.value, source=_source(td, prop, None)
                )
            )
    return result
