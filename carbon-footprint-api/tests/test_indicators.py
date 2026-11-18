"""Reference quantities from Technical Data."""

import pytest

from carbon_footprint_api.submodels.indicators import derive_indicators, normalize_name, parse_number
from carbon_footprint_api.submodels.models import PropertyArea, TechnicalData, TechnicalProperty


def _td(*props: dict) -> list[TechnicalData]:
    properties = [TechnicalProperty(modelType="Property", **p) for p in props]
    return [TechnicalData(submodelId="urn:td", areas=[PropertyArea(name="TechnicalProperties", properties=properties)])]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2,250", 2250.0), ("0,5", 0.5), ("1.5", 1.5), ("1.234,5", 1234.5), ("1,234.5", 1234.5), ("x", None)],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_normalize_name():
    assert normalize_name("Product_weight") == "product weight"
    assert normalize_name("heightMm") == "height mm"


def test_mass_from_value_with_unit_and_from_semantic_id():
    result = derive_indicators(_td({"idShort": "Product_weight", "value": "2,250 g"}))
    assert result.mass.value == pytest.approx(2.25) and result.mass.unit == "kg"
    assert result.mass.source.idShort == "Product_weight" and result.mass.source.unit == "g"
    net_weight = {"idShort": "X", "semanticId": "0173-1#02-BAD875#007", "value": "250.0", "unit": "g"}
    result = derive_indicators(_td(net_weight))
    assert result.mass.value == pytest.approx(0.25)


def test_wrong_units_and_other_weights_are_ignored():
    result = derive_indicators(
        _td(
            {"idShort": "Max__power_supply", "value": "8 A"},
            {"idShort": "Power", "value": "24 V"},
            {"idShort": "Slide_weight", "value": "55 g"},
            {"idShort": "Additional_weight_per_10_mm_stroke", "value": "52.5 g"},
            {"idShort": "Weight", "value": "no data"},
        )
    )
    assert result.mass is None and result.power is None


def test_power_dimensions_lifetime_and_materials():
    result = derive_indicators(
        _td(
            {"idShort": "Power_input_UL", "value": "7.68 W"},
            {"idShort": "Width", "value": "45", "unit": "mm"},
            {"idShort": "Height", "value": "105", "unit": "mm"},
            {"idShort": "depthMm", "value": "87"},
            {"idShort": "ServiceLife", "value": "10", "unit": "years"},
            {"idShort": "Material_housing", "value": "Aluminium"},
            {"idShort": "Materials_note", "value": "RoHS"},
        )
    )
    assert result.power.value == pytest.approx(7.68) and result.power.unit == "W"
    assert result.depth.value == pytest.approx(0.087)
    assert result.volume == pytest.approx(0.045 * 0.105 * 0.087)
    assert result.lifetime.value == 10 and result.lifetime.unit == "a"
    assert [m.value for m in result.materials] == ["Aluminium"]


def test_conflicting_values_produce_warning():
    result = derive_indicators(_td({"idShort": "Weight", "value": "1 kg"}, {"idShort": "Gewicht", "value": "900 g"}))
    assert result.mass.value == 1.0 and result.warnings


def test_endpoint(client):
    shells = client.get("/api/v4/shell-descriptors").json()["result"]
    assert shells
    r = client.get(f"/api/v4/products/{_b64(shells[0]['id'])}/indicators")
    assert r.status_code == 200 and "mass" in r.json()


def _b64(value: str) -> str:
    import base64

    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
