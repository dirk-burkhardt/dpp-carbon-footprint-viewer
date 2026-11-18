"""Estimates for life cycle phases without declared footprint."""

import pytest

from carbon_footprint_api.estimates import EstimateParameters, estimate
from carbon_footprint_api.estimates.data import classes, factors
from carbon_footprint_api.submodels.models import (
    CarbonFootprintResult,
    Classification,
    Footprint,
    FootprintSummary,
    Indicators,
    MaterialInfo,
    Measure,
    MeasureSource,
    TechnicalData,
)


def _measure(value: float, unit: str) -> Measure:
    return Measure(value=value, unit=unit, source=MeasureSource(idShort="X", value=str(value)))


def _td(system: str | None = None, class_id: str | None = None) -> list[TechnicalData]:
    classifications = [Classification(system=system, classId=class_id)] if system else []
    return [TechnicalData(classifications=classifications)]


def _footprints(*items: Footprint) -> CarbonFootprintResult:
    phases = sorted({p for f in items for p in f.lifeCyclePhases})
    return CarbonFootprintResult(footprints=list(items), summary=FootprintSummary(coveredPhases=phases))


def _phase(result, phase):
    return next(p for p in result.phases if p.phase == phase)


def test_factor_files_are_complete():
    data = factors()
    assert data["electricity"]["countries"]["DE"] > 0 and "EU" in data["electricity"]["countries"]
    assert set(data["freight"]) >= {"road", "rail", "sea", "air"}
    for entry in [*classes()["eclass"], *classes()["espr"].values(), classes()["default"]]:
        if entry["material"]:
            assert entry["material"] in data["materials"]
        for key in ("lifetime", "hoursPerYear"):
            if entry[key]:
                assert entry[key]["source"] in classes()["sources"]


def test_without_declared_footprint_all_phases_are_estimated():
    indicators = Indicators(mass=_measure(2.0, "kg"), power=_measure(10.0, "W"))
    result = estimate(
        _footprints(), indicators, _td("ECLASS", "27-27-01-05"), EstimateParameters(country="DE", transport_km=500)
    )
    assert result.productClass.label.startswith("ECLASS segment 27")
    material = factors()["materials"]["electrical-small"]
    assert _phase(result, "A1-A3").co2eq == pytest.approx(2.0 * material["productionKgCo2ePerKg"])
    road = factors()["freight"]["road"]["kgCo2ePerTonneKm"]
    assert _phase(result, "A4").co2eq == pytest.approx(0.002 * 500 * road)
    grid = factors()["electricity"]["countries"]["DE"]
    # ECLASS 27: 18 years (AfA 3.3.1), 4000 h per year
    assert _phase(result, "B6").co2eq == pytest.approx(10 * 4000 * 18 / 1000 * grid)
    b6 = _phase(result, "B6")
    assert {i.origin for i in b6.inputs} == {"file", "class", "factor"}
    assert _phase(result, "C1-C4").status == "estimated"
    assert result.estimatedCo2eq == pytest.approx(sum(p.co2eq for p in result.phases if p.status == "estimated"))
    assert {s.key for s in result.sources} >= {"afa-av", "dppviewer"}


def test_declared_phases_are_not_estimated_and_production_is_checked():
    declared = Footprint(
        kind="product",
        templateVersion="1.0",
        co2eq=100.0,
        lifeCyclePhases=["A1", "A2", "A3"],
        calculationMethods=["ISO 14067"],
    )
    use = Footprint(
        kind="product", templateVersion="1.0", co2eq=5.0, lifeCyclePhases=["B6"], calculationMethods=["ISO 14067"]
    )
    transport = Footprint(kind="transport", templateVersion="1.0", co2eq=1.0)
    result = _footprints(declared, use, transport)
    result.summary.primaryMethod = "ISO 14067"
    indicators = Indicators(mass=_measure(1.0, "kg"), power=_measure(10.0, "W"))
    out = estimate(result, indicators, _td("ECLASS", "27270105"), EstimateParameters())
    assert [p.status for p in out.phases] == ["declared", "declared", "declared", "estimated"]
    assert out.plausibility is not None and out.plausibility.assessment == "high"


def test_user_assumptions_override_class_defaults():
    indicators = Indicators(power=_measure(100.0, "W"))
    out = estimate(
        _footprints(), indicators, _td(), EstimateParameters(country="FR", lifetime_years=5, hours_per_year=1000)
    )
    b6 = _phase(out, "B6")
    grid = factors()["electricity"]["countries"]["FR"]
    assert b6.co2eq == pytest.approx(100 * 1000 * 5 / 1000 * grid)
    assert {i.origin for i in b6.inputs if i.unit in ("a", "h/a")} == {"user"}
    assert out.productClass.label == classes()["default"]["label"]


def test_missing_inputs_are_explained():
    out = estimate(_footprints(), Indicators(), _td(), EstimateParameters())
    assert all(p.status == "missing" and p.reason for p in out.phases)
    assert out.estimatedCo2eq == 0


def test_material_from_technical_data_and_unknown_country():
    indicators = Indicators(
        mass=_measure(1.0, "kg"),
        materials=[MaterialInfo(name="Material housing", value="Wrought aluminium alloy", source=MeasureSource())],
    )
    out = estimate(_footprints(), indicators, _td(), EstimateParameters(country="XX"))
    assert out.material is not None and out.material.origin == "file" and "aluminium" in out.material.name
    assert _phase(out, "A1-A3").status == "estimated"


def test_phases_without_information_produce_warning():
    declared = Footprint(kind="product", templateVersion="1.0", co2eq=42.0)
    out = estimate(_footprints(declared), Indicators(), _td(), EstimateParameters())
    assert out.warnings


def test_endpoint(client):
    shells = client.get("/api/v4/shell-descriptors").json()["result"]
    import base64

    shell_id = base64.urlsafe_b64encode(shells[0]["id"].encode()).decode().rstrip("=")
    r = client.get(f"/api/v4/products/{shell_id}/estimates", params={"country": "DE", "transportKm": 100})
    assert r.status_code == 200 and len(r.json()["phases"]) == 4
    assert client.get(f"/api/v4/products/{shell_id}/estimates", params={"country": "Germany"}).status_code == 400
