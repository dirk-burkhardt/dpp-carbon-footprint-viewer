"""Parser für IDTA-Submodel-Templates: Erkennung aller bekannten Versionen, Normalisierung, Zusammenfassung."""

import copy
import json
import tarfile
from pathlib import Path

import pytest

from carbon_footprint_api.aas.model import parse_json
from carbon_footprint_api.submodels import (
    detect,
    families,
    parse_carbon_footprint,
    parse_handover_documentation,
    parse_hierarchy,
    parse_maintenance_instructions,
    parse_nameplate,
    parse_technical_data,
    summarize,
)
from carbon_footprint_api.submodels.lifecycle import parse_phases
from carbon_footprint_api.submodels.models import Footprint
from carbon_footprint_api.submodels.query import normalize_semantic_id, resolve_value_id
from conftest import TESTS

ARCHIVE = TESTS / "idta_templates.tar.gz"
# Familie im Archiv -> erwartete erkannte Familie
DETECTED_AS = {"battery-carbon-footprint": "carbon-footprint"}


def _templates() -> dict[str, bytes]:
    if not ARCHIVE.exists():
        return {}
    with tarfile.open(ARCHIVE) as tar:
        return {
            m.name: tar.extractfile(m).read()  # type: ignore[union-attr]
            for m in tar.getmembers()
            if m.isfile()
        }


TEMPLATES = _templates()


def _template(family: str, version: str, contains: str = "") -> dict:
    for name, data in TEMPLATES.items():
        _, fam, rest = name.split("/", 2)
        if fam == family and rest.rsplit("/", 1)[0] == version and contains in name and "V3.1" not in name:
            return json.loads(data)
    raise AssertionError(f"Kein Template {family} {version}")


# --------------------------------------------------------------------------------------------------------------
# Grundfunktionen
# --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("A1 - raw material supply (and upstream production)", ["A1"]),
        ("A1-A3", ["A1", "A2", "A3"]),
        ("A1–A3, C2", ["A1", "A2", "A3", "C2"]),
        ("A4-A5", ["A4", "A5"]),
        ("B1-B7", ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]),
        ("D - reuse", ["D"]),
        ("A1;A2", ["A1", "A2"]),
        ("", []),
        ("unbekannt", []),
    ],
)
def test_parse_phases(value, expected):
    assert parse_phases(value) == expected


def test_phases_from_list():
    assert parse_phases(["C4 - landfill", "A2 - cradle-to-gate transport to factory"]) == ["A2", "C4"]


def test_semantic_id_normalization():
    assert normalize_semantic_id("0173-1#02-ABG854#003") == "0173-1#02-ABG854"
    assert normalize_semantic_id("0112/2///61987#ABA565#009") == "0112/2///61987#ABA565"
    url = "https://admin-shell.io/idta/CarbonFootprint/CarbonFootprint/1/0"
    assert normalize_semantic_id(url + "/") == url
    assert normalize_semantic_id("urn:samm:x:1.0.0#performanceClass") == "urn:samm:x:1.0.0#performanceClass"


def test_value_ids():
    assert resolve_value_id("0173-1#07-ABU221#002") == "GHG Protocol"
    assert resolve_value_id("0173-1#07-ABU212#001") == "B1 - usage phase"
    assert resolve_value_id("GHG Protocol") is None


# --------------------------------------------------------------------------------------------------------------
# Alle Templates von GitHub (tests/idta_templates.tar.gz, erzeugt mit tools/check_idta_templates.py --fixtures)
# --------------------------------------------------------------------------------------------------------------


@pytest.mark.skipif(not TEMPLATES, reason="Template-Archiv fehlt")
def test_every_known_version_has_a_template():
    available = {tuple(name.split("/")[1:-1]) for name in TEMPLATES}
    for fam in families():
        for version in fam.known_versions:
            if version in fam.without_json_template:
                continue
            assert (fam.key, *version.split("/")) in available, f"{fam.key} {version} fehlt im Archiv"


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_template_is_detected_and_parsed(name):
    family_key, version = name.split("/")[1], "/".join(name.split("/")[2:-1])
    env = parse_json(json.loads(TEMPLATES[name]))
    assert env.submodels, name
    fam = next(f for f in families() if f.key == family_key)
    for submodel in env.submodels:
        info = detect(submodel)
        assert info.family == DETECTED_AS.get(family_key, family_key), name
        assert info.version in fam.semantic_ids.values() or family_key in DETECTED_AS, name
        assert version.replace("/", ".").startswith(info.version.split(" ")[-1]) or family_key in DETECTED_AS, name
        # Parser laufen ohne Fehler, auch auf leeren Templates
        parse_carbon_footprint(submodel, info)
        parse_nameplate(submodel, info)
        parse_hierarchy(submodel)
        parse_technical_data(submodel, info)
        parse_handover_documentation(submodel, info)
        parse_maintenance_instructions(submodel, info)


@pytest.mark.skipif(not TEMPLATES, reason="Template-Archiv fehlt")
@pytest.mark.parametrize("version", ["1/0", "1/0/1", "1/0/2", "1/0/3"])
def test_carbon_footprint_1_0_structure(version):
    submodel = parse_json(_template("carbon-footprint", version))
    info = detect(submodel.submodels[0])
    assert (info.version, info.variant) == ("1.0", None)


@pytest.mark.skipif(not TEMPLATES, reason="Template-Archiv fehlt")
def test_battery_passport_profile():
    data = _template("battery-carbon-footprint", "1/0/2")
    data["submodels"][0]["kind"] = "Instance"
    env = parse_json(data)
    info = detect(env.submodels[0])
    assert info.family == "carbon-footprint"
    assert info.variant and "02035-3" in info.variant
    footprints = parse_carbon_footprint(env.submodels[0], info)
    assert footprints[0].publicStudyLinks == ["XF90-884"]


def _filled_cf_1_0() -> dict:
    """Template 1.0.3 mit zwei ausgefüllten PCFs (A1-A3 und A4) und einem sektorspezifischen Eintrag."""
    data = _template("carbon-footprint", "1/0/3")
    sm = data["submodels"][0]
    sm["kind"] = "Instance"
    pcfs = next(e for e in sm["submodelElements"] if e["idShort"] == "ProductCarbonFootprints")
    template = pcfs["value"][0]

    def fill(phase: str, co2: str) -> dict:
        item = copy.deepcopy(template)
        for el in item["value"]:
            match el["idShort"]:
                case "PcfCalculationMethods":
                    el["value"][0]["value"] = "ISO 14067"
                case "PcfCO2eq":
                    el["value"] = co2
                case "ReferenceImpactUnitForCalculation":
                    el["value"] = "piece"
                case "QuantityOfMeasureForCalculation":
                    el["value"] = "1"
                case "LifeCyclePhases":
                    el["value"][0]["value"] = phase
        return item

    pcfs["value"] = [fill("A1-A3", "2.5"), fill("A4 - transport to final destination", "0.4")]
    sector = next(e for e in sm["submodelElements"] if e["idShort"] == "ProductOrSectorSpecificCarbonFootprints")
    rule = next(e for e in sector["value"][0]["value"] if e["idShort"] == "ProductOrSectorSpecificRule")
    next(e for e in rule["value"] if e["idShort"] == "PcfRuleName")["value"] = "PCR Elektronik"
    return data


@pytest.mark.skipif(not TEMPLATES, reason="Template-Archiv fehlt")
def test_carbon_footprint_1_0_values():
    submodel = parse_json(_filled_cf_1_0()).submodels[0]
    footprints = parse_carbon_footprint(submodel)
    products = [f for f in footprints if f.kind == "product"]
    assert [(f.co2eq, f.lifeCyclePhases, f.calculationMethods) for f in products] == [
        (2.5, ["A1", "A2", "A3"], ["ISO 14067"]),
        (0.4, ["A4"], ["ISO 14067"]),
    ]
    assert products[0].idShortPath == "ProductCarbonFootprints[0]"
    sector = next(f for f in footprints if f.kind == "productOrSectorSpecific")
    assert sector.rule is not None and sector.rule.name == "PCR Elektronik"
    summary = summarize(footprints)
    assert summary.primaryMethod == "ISO 14067"
    assert summary.totalCo2eq == pytest.approx(2.9)
    assert summary.coveredPhases == ["A1", "A2", "A3", "A4"]


# --------------------------------------------------------------------------------------------------------------
# Zusammenfassung
# --------------------------------------------------------------------------------------------------------------


def _fp(co2, phases, method="ISO 14067", kind="product"):
    return Footprint(
        kind=kind, templateVersion="1.0", co2eq=co2, calculationMethods=[method], lifeCyclePhases=parse_phases(phases)
    )


def test_summary_skips_overlapping_phases():
    fps = [_fp(3.0, "A1-A3"), _fp(1.0, "A1"), _fp(1.0, "A2"), _fp(1.5, "A3")]
    summary = summarize(fps)
    assert summary.productCo2eq == pytest.approx(3.5)
    assert summary.methods[0].skippedEntries == [0]
    assert summary.warnings


def test_summary_never_adds_methods():
    fps = [_fp(2.0, "A1-A3", "GHG Protocol"), _fp(3.0, "A1-A3", "ISO 14067"), _fp(1.0, "C4", "EN 15804")]
    summary = summarize(fps)
    assert summary.primaryMethod == "ISO 14067"
    assert summary.productCo2eq == pytest.approx(3.0)
    assert {m.method: m.co2eq for m in summary.methods} == {"GHG Protocol": 2.0, "ISO 14067": 3.0, "EN 15804": 1.0}


def test_summary_first_method_without_preference():
    summary = summarize([_fp(1.0, "A1", "PACT v3.0.0"), _fp(2.0, "A1", "TFS v3")])
    assert summary.primaryMethod == "PACT v3.0.0"


def test_summary_adds_every_transport_leg():
    fps = [_fp(1.0, "A1-A3"), _fp(0.2, "", "EN 16258", "transport"), _fp(0.3, "", "EN 16258", "transport")]
    summary = summarize(fps)
    assert summary.transportCo2eq == pytest.approx(0.5)
    assert summary.totalCo2eq == pytest.approx(1.5)
    assert "A4" in summary.coveredPhases


def test_summary_ignores_missing_values():
    summary = summarize([_fp(None, "A1"), _fp(1.0, "A2")])
    assert summary.totalCo2eq == pytest.approx(1.0)


# --------------------------------------------------------------------------------------------------------------
# Beispieldateien im Ordner repo
# --------------------------------------------------------------------------------------------------------------


def _shell(provider, id_short: str) -> str:
    return next(i for i, s in provider.available_shell_ids().items() if s == id_short)


def test_repo_versions(repo_provider):
    from carbon_footprint_api.services import ProductService

    service = ProductService(repo_provider)
    festo = service.carbon_footprint(_shell(repo_provider, "AAS_DPDM-Q-10-30-PA_1"))
    assert {f.templateVersion for f in festo.footprints} == {"1.0-Entwurf"}
    assert festo.summary.totalCo2eq == pytest.approx(12.2)

    phone = service.carbon_footprint(_shell(repo_provider, "Fairphone-One"))
    assert {f.templateVersion for f in phone.footprints} == {"0.9"}
    assert phone.summary.primaryMethod == "ISO 14044"
    assert len(phone.summary.methods[0].skippedEntries) == 1  # A1-A3 neben A1, A2, A3


def test_repo_product_tree(repo_provider):
    from carbon_footprint_api.services import ProductService

    tree = ProductService(repo_provider).product_tree(_shell(repo_provider, "Fairphone-One"))
    assert tree is not None
    assert (tree.archeType, tree.hierarchyVersion, tree.nodeCount) == ("OneDown", "1.0", 14)
    screws = {c.idShort: c.bulkCount for c in tree.root.children}
    assert screws["Fairphone-CopperScrew"] == 6
    mainboard = next(c for c in tree.root.children if c.idShort == "Fairphone-Mainboard-Part1")
    assert len(mainboard.children) == 5


def test_template_copies_are_ignored(repo_provider):
    from carbon_footprint_api.services import ProductService

    templates = ProductService(repo_provider).templates(_shell(repo_provider, "Fairphone-One"))
    hs = [t for t in templates if t.family == "hierarchical-structures"]
    assert sorted((t.version, t.isTemplate) for t in hs) == [("1.0", False), ("1.1", True)]


def test_archive_paths_are_safe():
    for name in TEMPLATES:
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
