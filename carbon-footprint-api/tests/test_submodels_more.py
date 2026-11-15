"""Technical Data, Handover Documentation und Maintenance Instructions in allen bekannten Versionen."""

import copy

import pytest

from carbon_footprint_api.aas.model import parse_json
from carbon_footprint_api.services import ProductService
from carbon_footprint_api.submodels import (
    Semantics,
    detect,
    parse_handover_documentation,
    parse_maintenance_instructions,
    parse_technical_data,
)
from carbon_footprint_api.submodels.structure import base_name
from test_submodels import TEMPLATES, _shell, _template

pytestmark = pytest.mark.skipif(not TEMPLATES, reason="Template-Archiv fehlt")


def _instance(data: dict):
    env = parse_json(data)
    for sm in env.submodels:
        sm["kind"] = "Instance"
    cds = {c["id"]: c for c in env.concept_descriptions}
    return env.submodels[0], Semantics(cds.get)


@pytest.mark.parametrize(
    ("id_short", "expected"),
    [("Document01", "document"), ("Document__00__", "document"), ("Alarm{00}", "alarm"), ("Language_2", "language")],
)
def test_base_name(id_short, expected):
    assert base_name(id_short) == expected


def test_technical_data_2_0_sample():
    submodel, semantics = _instance(_template("technical-data", "2/0", "Sample"))
    td = parse_technical_data(submodel, detect(submodel), semantics)
    assert td is not None
    assert (td.templateVersion, td.manufacturerName, td.articleNumber) == ("2.0", "Manufacturer AG", "12345")
    assert len(td.productImages) == 2
    assert {c.system for c in td.classifications} >= {"ECLASS", "IEC CDD"}
    properties = [p for area in td.areas for p in area.properties]
    assert properties and all(p.value is not None or p.min is not None or p.max is not None for p in properties)
    diameter = next(p for p in properties if p.idShort == "diameter")
    assert diameter.name  # aus der ConceptDescription der Datei
    assert any(p.unit for p in properties)


def test_handover_documentation_2_0_example():
    submodel, _ = _instance(_template("handover-documentation", "2/0", "Example"))
    hd = parse_handover_documentation(submodel)
    assert hd is not None and hd.documents
    doc = hd.documents[0]
    assert doc.ids[0].id == "123-ABC-456" and doc.ids[0].isPrimary is True
    assert doc.classifications[0].classId == "02-01"
    version = doc.versions[0]
    assert version.languages == ["en"]
    assert version.digitalFiles[0].path.endswith(".pdf")
    assert version.previewFile is not None


def test_handover_documentation_1_2_template():
    data = copy.deepcopy(_template("handover-documentation", "1/2"))
    submodel, _ = _instance(data)
    hd = parse_handover_documentation(submodel)
    assert hd is not None and hd.templateVersion == "1.2"
    assert hd.documents[0].ids[0].isPrimary is True


def test_maintenance_instructions_filled():
    data = copy.deepcopy(_template("maintenance-instructions", "1/0/2"))
    sm = data["submodels"][0]

    def set_value(element: dict, path: list[str], value):
        for name in path[:-1]:
            element = next(e for e in element.get("value") or element["submodelElements"] if e.get("idShort") == name)
        target = next(e for e in element["value"] if e.get("idShort") == path[-1])
        target["value"] = value

    interval = "MaintenanceInstructionsForSpecificInterval__00__"
    basic = [interval, "BasicMaintenanceInformation"]
    set_value(sm, [*basic, "MaintenanceID"], "M-1")
    set_value(sm, [*basic, "NameOfMaintenance"], [{"language": "de", "text": "Jahreswartung"}])
    set_value(sm, [*basic, "IntervalSpecification", "MaintenanceIntervalValue"], "12")
    set_value(sm, [*basic, "IntervalSpecification", "MaintenanceIntervalUnit"], "month")
    steps = [interval, "ListMaintenanceSteps", "MaintenanceStep__00__"]
    set_value(sm, [*steps, "MaintenanceStepID"], "S-1")
    set_value(sm, [*steps, "QuantityOfToolsForMaintenanceStep"], "2")
    tool = next(e for e in sm["submodelElements"] if e["idShort"] == "MaintenanceToolList")["value"][0]
    next(e for e in tool["value"] if e["idShort"] == "ToolID")["value"] = "T-7"
    submodel, _ = _instance(data)
    mi = parse_maintenance_instructions(submodel)
    assert mi is not None and mi.templateVersion == "1.0"
    first = mi.intervals[0]
    assert (first.id, first.name, first.interval.value, first.interval.unit) == ("M-1", "Jahreswartung", 12, "month")
    assert first.contact is not None and first.contact.cityTown == "Musterstadt"
    assert first.steps[0].id == "S-1" and first.steps[0].tools[0].quantity == 2
    assert [t.id for t in mi.tools] == ["T-7"]


def test_repo_technical_data_and_documents(repo_provider):
    service = ProductService(repo_provider)
    switch = _shell(repo_provider, "AAS_Festo_Series_579071")
    td = service.technical_data(switch)[0]
    assert td.classifications[0].classId == "27-27-01-05"
    design = next(p for a in td.areas for p in a.properties if (p.idShort or "").strip() == "Design")
    assert (design.path, design.value) == (["Common properties"], "for T-slot")
    docs = service.documentation(switch)
    assert {d.templateVersion for d in docs} == {"VDI 2770 1.0"}
    eplan = next(doc for d in docs for doc in d.documents if doc.idShortPath == "EPLAN")
    assert eplan.versions[0].languages[:2] == ["en", "de"]


def test_repo_concept_descriptions(repo_provider):
    cd = repo_provider.get_concept_description("0173-1#02-ABG855#003")  # gespeichert als #001---<Anhang>
    assert cd is not None and cd["id"].startswith("0173-1#02-ABG855")


def test_details_endpoint(client):
    import base64

    shells = client.get("/api/v4/asset/all").json()
    shell = next(i for i, s in shells.items() if s == "AAS_DPDM-Q-10-30-PA_1")
    encoded = base64.urlsafe_b64encode(shell.encode()).decode().rstrip("=")
    data = client.get(f"/api/v4/products/{encoded}/details").json()
    assert data["nameplate"]["manufacturerName"] == "Festo SE & Co. KG"
    assert data["technicalData"][0]["areas"][0]["properties"]
    assert data["documentation"][0]["documents"]
    for path in ("technical-data", "documentation", "maintenance"):
        assert client.get(f"/api/v4/products/{encoded}/{path}").status_code == 200
    cd = base64.urlsafe_b64encode(b"0173-1#02-ABG855#001").decode().rstrip("=")
    assert client.get(f"/api/v4/concept-descriptions/{cd}").status_code == 200
    assert client.get(f"/api/v4/concept-descriptions/{base64.urlsafe_b64encode(b'x').decode()}").status_code == 404


def test_every_template_family_has_a_parser():
    from carbon_footprint_api.submodels import families

    assert {f.key: f.parsing for f in families()} == {f.key: "full" for f in families()}
