import base64
import json

import pytest

from carbon_footprint_api.aas import AasParseError, AssetType, parse_json, parse_xml, read_environment, walk
from carbon_footprint_api.aas.model import enum_value
from carbon_footprint_api.repository import split_id_short_path
from conftest import REPO


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("xs:string", "String"),
        ("xs:gYear", "Gyear"),
        ("xs:dateTime", "DateTime"),
        ("xs:anyURI", "AnyUri"),
        ("xs:base64Binary", "Base64binary"),
        ("xs:nonNegativeInteger", "NonNegativeInteger"),
        ("ExternalReference", "ExternalReference"),
        ("SelfManagedEntity", "SelfManagedEntity"),
        ("NotApplicable", "NotApplicable"),
        ("STRING_TRANSLATABLE", "StringTranslatable"),
        ("IRDI", "Irdi"),
        (None, None),
        ("", None),
    ],
)
def test_enum_value(raw, expected):
    assert enum_value(raw) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a", ["a"]),
        ("a.b.c", ["a", "b", "c"]),
        ("a[0]", ["a", "[0]"]),
        ("a.b[2].c", ["a", "b", "[2]", "c"]),
        ("a[1][2]", ["a", "[1]", "[2]"]),
        ("a..b", ["a", "", "b"]),
        ("a.", ["a"]),
        ("", []),
    ],
)
def test_split_id_short_path(path, expected):
    assert split_id_short_path(path) == expected


XML = b"""<?xml version="1.0"?>
<environment xmlns="https://admin-shell.io/aas/3/0">
  <assetAdministrationShells><assetAdministrationShell>
    <idShort>S</idShort><id>urn:shell</id>
    <assetInformation><assetKind>Instance</assetKind></assetInformation>
    <submodels><reference><type>ModelReference</type><keys><key><type>Submodel</type><value>urn:sm</value></key></keys></reference></submodels>
  </assetAdministrationShell></assetAdministrationShells>
  <submodels><submodel>
    <idShort>SM</idShort><id>urn:sm</id>
    <submodelElements>
      <property><idShort>P1</idShort><valueType>xs:int</valueType><value>1</value>
        <qualifiers><qualifier><type>Q</type><valueType>xs:string</valueType></qualifier></qualifiers></property>
      <submodelElementCollection><idShort>C</idShort><value>
        <property><idShort>Inner</idShort><valueType>xs:string</valueType><value>x</value></property>
      </value></submodelElementCollection>
      <property><idShort>P2</idShort><valueType>xs:boolean</valueType><value>true</value></property>
      <blob><idShort>B</idShort><value>aGFsbG8=</value><contentType>text/plain</contentType></blob>
    </submodelElements>
  </submodel></submodels>
</environment>"""


def test_parse_xml_api_format():
    env = parse_xml(XML)
    shell = env.shells[0]
    assert shell["assetInformation"] == {
        "assetKind": "Instance",
        "assetType": None,
        "defaultThumbnail": None,
        "globalAssetId": None,
        "specificAssetIds": [],
    }
    assert shell["submodels"][0]["type"] == "ModelReference"
    submodel = env.submodels[0]
    assert submodel["kind"] == "Instance"
    # Gruppierung nach Elementtyp: erst alle Properties, dann Collection, dann Blob
    assert [e["idShort"] for e in submodel["submodelElements"]] == ["P1", "P2", "C", "B"]
    p1 = submodel["submodelElements"][0]
    assert list(p1) == [
        "embeddedDataSpecifications",
        "extensions",
        "semanticId",
        "supplementalSemanticIds",
        "value",
        "valueId",
        "valueType",
        "qualifiers",
        "category",
        "description",
        "displayName",
        "idShort",
    ]
    assert p1["valueType"] == "Int" and p1["qualifiers"][0]["kind"] == "ConceptQualifier"
    assert submodel["submodelElements"][3]["value"] == base64.b64encode(b"hallo").decode()
    assert "modelType" not in json.dumps(submodel)


def test_parse_json_matches_xml():
    spec = {
        "assetAdministrationShells": [
            {
                "modelType": "AssetAdministrationShell",
                "idShort": "S",
                "id": "urn:shell",
                "assetInformation": {"assetKind": "Instance"},
                "submodels": [{"type": "ModelReference", "keys": [{"type": "Submodel", "value": "urn:sm"}]}],
            }
        ],
        "submodels": [
            {
                "modelType": "Submodel",
                "idShort": "SM",
                "id": "urn:sm",
                "submodelElements": [
                    {
                        "modelType": "Property",
                        "idShort": "P1",
                        "valueType": "xs:int",
                        "value": "1",
                        "qualifiers": [{"type": "Q", "valueType": "xs:string"}],
                    },
                    {"modelType": "Property", "idShort": "P2", "valueType": "xs:boolean", "value": "true"},
                    {
                        "modelType": "SubmodelElementCollection",
                        "idShort": "C",
                        "value": [
                            {"modelType": "Property", "idShort": "Inner", "valueType": "xs:string", "value": "x"}
                        ],
                    },
                    {"modelType": "Blob", "idShort": "B", "value": "aGFsbG8=", "contentType": "text/plain"},
                ],
            }
        ],
    }
    from_json = parse_json(spec)
    from_xml = parse_xml(XML)
    assert from_json.shells == from_xml.shells
    assert from_json.submodels == from_xml.submodels


def test_invalid_data():
    with pytest.raises(AasParseError):
        read_environment(b"kein AAS", AssetType.AUTO)
    with pytest.raises(AasParseError):
        parse_xml(b"<foo/>")


@pytest.mark.skipif(not (REPO / "test_demo_full_example.xml").exists(), reason="Demo-Datei fehlt")
def test_all_element_types():
    env, suffix = read_environment((REPO / "test_demo_full_example.xml").read_bytes(), AssetType.AUTO)
    assert suffix == ".xml"
    types = {e.model_type for s in env.submodels for e in walk(s["submodelElements"])}
    assert types == {
        "Property",
        "MultiLanguageProperty",
        "Range",
        "File",
        "Blob",
        "ReferenceElement",
        "RelationshipElement",
        "AnnotatedRelationshipElement",
        "Entity",
        "SubmodelElementCollection",
        "SubmodelElementList",
        "Operation",
        "Capability",
        "BasicEventElement",
    }
