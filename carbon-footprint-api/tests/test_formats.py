"""Kompatibilität mit den Formatspezifikationen: offizielle Beispiele aller bekannten Metamodell- und AASX-Versionen.

Die Beispiele stammen aus aas-specs-metamodel (gültige ``maximal``/``minimal``-Beispiele jeder Klasse, je
Minor-Version das neueste Release) und aas-specs-aasx. Erzeugt mit ``tools/check_idta_templates.py --fixtures``.
"""

import json
import tarfile

import pytest

from carbon_footprint_api.aas.model import parse_json, parse_xml
from carbon_footprint_api.aas.package import read_aasx
from conftest import TESTS

ARCHIVE = TESTS / "aas_format_examples.tar.gz"
# Bewusst nicht übernommen: ConceptDescriptions (die API liefert keine aus) und modelType (kein Teil des Formats)
NOT_CARRIED = {"conceptDescriptions", "modelType", "assetAdministrationShells", "submodels"}


def _examples() -> dict[str, bytes]:
    if not ARCHIVE.exists():
        return {}
    with tarfile.open(ARCHIVE) as tar:
        return {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}  # type: ignore[union-attr]


EXAMPLES = _examples()
METAMODEL = sorted(n for n in EXAMPLES if n.split("/")[1] == "metamodel")
AASX = sorted(n for n in EXAMPLES if n.split("/")[1] == "aasx")


def _parse(name: str):
    data = EXAMPLES[name]
    return parse_json(json.loads(data)) if name.endswith(".json") else parse_xml(data)


def _as_json(env) -> list:
    return json.loads(json.dumps([*env.shells, *env.submodels]))


def _keys(value, found: set[str]) -> set[str]:
    if isinstance(value, dict):
        for k, v in value.items():
            found.add(k)
            _keys(v, found)
    elif isinstance(value, list):
        for v in value:
            _keys(v, found)
    return found


def _without_concept_descriptions(data: dict) -> dict:
    return {k: v for k, v in data.items() if k != "conceptDescriptions"}


@pytest.mark.parametrize("name", METAMODEL)
def test_metamodel_example_is_read(name):
    env = _parse(name)
    lowered = name.lower()
    assert env.shells or env.submodels or "conceptdescription" in lowered or "dataspecification" in lowered


@pytest.mark.parametrize("name", [n for n in METAMODEL if n.endswith("maximal.json")])
def test_no_attribute_is_lost(name):
    """Jedes Attribut der Beispiele (außer ConceptDescriptions) kommt in der Antwort an."""
    data = _without_concept_descriptions(json.loads(EXAMPLES[name]))
    lost = _keys(data, set()) - _keys(_as_json(_parse(name)), set()) - NOT_CARRIED
    assert not lost, f"{name}: nicht übernommen: {sorted(lost)}"


# XML-Beispiele liegen in Ordnern mit kleinem Anfangsbuchstaben (property statt Property)
_XML_BY_KEY = {n.lower().replace("/xml/", "/json/")[: -len(".xml")]: n for n in METAMODEL if n.endswith(".xml")}


@pytest.mark.parametrize("name", [n for n in METAMODEL if n.endswith(".json")])
def test_xml_and_json_give_the_same_result(name):
    xml_name = _XML_BY_KEY.get(name.lower()[: -len(".json")])
    if xml_name is None:
        pytest.skip("kein XML-Gegenstück")
    assert _as_json(_parse(xml_name)) == _as_json(_parse(name))


@pytest.mark.parametrize("name", AASX)
def test_aasx_example_is_read(name):
    env = read_aasx(EXAMPLES[name])
    assert env.shells and env.submodels


@pytest.mark.skipif(not EXAMPLES, reason="Archiv fehlt")
def test_all_known_versions_are_covered():
    versions = {tuple(n.split("/")[1:3]) for n in EXAMPLES}
    assert {("metamodel", "3.0.9"), ("metamodel", "3.1.2"), ("metamodel", "3.2.0")} <= versions
    assert {("aasx", "3.1.0"), ("aasx", "3.2.0")} <= versions
