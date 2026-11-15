"""Umwandlung von AAS-3.0-Daten (XML oder spezifikationskonformes JSON) in das JSON-Format der API.

Die API verwendet ein eigenes, vom spezifikationskonformen AAS-JSON abweichendes Format, das das Frontend
erwartet:

* es gibt kein ``modelType``, der Elementtyp ergibt sich nur aus den vorhandenen Feldern
* alle Felder werden ausgegeben, fehlende Werte als ``null``, fehlende Listen als ``[]``
* Enums stehen in CamelCase ihres Namens in GROSSBUCHSTABEN (``xs:string`` wird ``String``, ``xs:gYear`` wird ``Gyear``)
* Blob-Werte sind Base64-codiert

Jedes erzeugte Objekt ist ein :class:`AasObject`, also ein normales ``dict`` mit zusätzlichem Attribut
``model_type``. Das Attribut wird nicht serialisiert, erlaubt aber Typprüfungen im Code.
"""

from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Callable, Iterable
from typing import Any, Optional

from lxml import etree


class AasParseError(ValueError):
    """Die Daten sind kein gültiges AAS-Environment."""


class AasObject(dict):
    """dict mit dem AAS-Typ (z. B. ``Property``) als nicht serialisiertes Attribut."""

    __slots__ = ("model_type",)

    def __init__(self, model_type: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model_type = model_type


# --------------------------------------------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------------------------------------------

# Enum-Namen der XSD-Datentypen (DataTypeDefXsd)
_XSD_TO_ENUM = {
    "xs:anyURI": "ANY_URI",
    "xs:base64Binary": "BASE64BINARY",
    "xs:boolean": "BOOLEAN",
    "xs:byte": "BYTE",
    "xs:date": "DATE",
    "xs:dateTime": "DATE_TIME",
    "xs:decimal": "DECIMAL",
    "xs:double": "DOUBLE",
    "xs:duration": "DURATION",
    "xs:float": "FLOAT",
    "xs:gDay": "GDAY",
    "xs:gMonth": "GMONTH",
    "xs:gMonthDay": "GMONTH_DAY",
    "xs:gYear": "GYEAR",
    "xs:gYearMonth": "GYEAR_MONTH",
    "xs:hexBinary": "HEX_BINARY",
    "xs:int": "INT",
    "xs:integer": "INTEGER",
    "xs:long": "LONG",
    "xs:negativeInteger": "NEGATIVE_INTEGER",
    "xs:nonNegativeInteger": "NON_NEGATIVE_INTEGER",
    "xs:nonPositiveInteger": "NON_POSITIVE_INTEGER",
    "xs:positiveInteger": "POSITIVE_INTEGER",
    "xs:short": "SHORT",
    "xs:string": "STRING",
    "xs:time": "TIME",
    "xs:unsignedByte": "UNSIGNED_BYTE",
    "xs:unsignedInt": "UNSIGNED_INT",
    "xs:unsignedLong": "UNSIGNED_LONG",
    "xs:unsignedShort": "UNSIGNED_SHORT",
}
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_UPPER_SNAKE = re.compile(r"[A-Z0-9_]+")


def enum_value(value: Optional[str]) -> Optional[str]:
    """Wandelt einen AAS-Enum-Wert in die Darstellung der API um (CamelCase des Enum-Namens)."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    name = _XSD_TO_ENUM.get(value)
    if name is None:
        if value.startswith("xs:"):
            value = value[3:]
        name = value if _UPPER_SNAKE.fullmatch(value) else _CAMEL_BOUNDARY.sub("_", value).upper()
    return "".join(word[0] + word[1:].lower() for word in name.split("_") if word)


# --------------------------------------------------------------------------------------------------------------
# Datenquellen: XML und JSON werden über dieselbe kleine Schnittstelle gelesen
# --------------------------------------------------------------------------------------------------------------


class _Source:
    """Lesezugriff auf ein AAS-Objekt, unabhängig davon, ob es aus XML oder JSON stammt."""

    model_type: Optional[str]

    def text(self, name: str) -> Optional[str]:
        raise NotImplementedError

    def obj(self, name: str) -> Optional[_Source]:
        raise NotImplementedError

    def items(self, name: str) -> list[_Source]:
        raise NotImplementedError

    def typed(self, name: str) -> Optional[_Source]:
        """Ein Kindobjekt, dessen Typ sich aus ihm selbst ergibt (z. B. ``OperationVariable.value``)."""
        raise NotImplementedError

    def flag(self, name: str) -> Optional[bool]:
        raise NotImplementedError


def _local(tag: Any) -> Optional[str]:
    if not isinstance(tag, str):
        return None  # Kommentare, Processing Instructions
    return tag.rpartition("}")[2]


class _XmlSource(_Source):
    __slots__ = ("el", "model_type")

    def __init__(self, el: etree._Element) -> None:
        self.el = el
        local = _local(el.tag) or ""
        self.model_type = local[:1].upper() + local[1:]

    def _child(self, name: str) -> Optional[etree._Element]:
        for child in self.el:
            if _local(child.tag) == name:
                return child
        return None

    def text(self, name: str) -> Optional[str]:
        child = self._child(name)
        if child is None:
            return None
        return child.text or ""

    def obj(self, name: str) -> Optional[_Source]:
        child = self._child(name)
        return None if child is None else _XmlSource(child)

    def items(self, name: str) -> list[_Source]:
        child = self._child(name)
        if child is None:
            return []
        return [_XmlSource(c) for c in child if _local(c.tag) is not None]

    def typed(self, name: str) -> Optional[_Source]:
        child = self._child(name)
        if child is None:
            return None
        for c in child:
            if _local(c.tag) is not None:
                return _XmlSource(c)
        return None

    def flag(self, name: str) -> Optional[bool]:
        value = self.text(name)
        return None if value is None else value.strip().lower() in ("true", "1")


class _JsonSource(_Source):
    __slots__ = ("data", "model_type")

    def __init__(self, data: dict) -> None:
        self.data = data
        self.model_type = data.get("modelType")

    def text(self, name: str) -> Optional[str]:
        value = self.data.get(name)
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            raise AasParseError(f"Feld {name} ist kein einfacher Wert")
        return str(value)

    def obj(self, name: str) -> Optional[_Source]:
        value = self.data.get(name)
        return _JsonSource(value) if isinstance(value, dict) else None

    def items(self, name: str) -> list[_Source]:
        value = self.data.get(name)
        if not isinstance(value, list):
            return []
        return [_JsonSource(v) for v in value if isinstance(v, dict)]

    def typed(self, name: str) -> Optional[_Source]:
        return self.obj(name)

    def flag(self, name: str) -> Optional[bool]:
        value = self.data.get(name)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1")
        return bool(value)


# --------------------------------------------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------------------------------------------


def _list(src: _Source, name: str, build: Callable[[_Source], Any]) -> list:
    return [build(item) for item in src.items(name)]


def _lang_string(src: _Source) -> AasObject:
    return AasObject("LangString", language=src.text("language"), text=src.text("text"))


def _key(src: _Source) -> AasObject:
    return AasObject("Key", type=enum_value(src.text("type")), value=src.text("value"))


def _reference(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    return AasObject(
        "Reference",
        keys=_list(src, "keys", _key),
        referredSemanticId=_reference(src.obj("referredSemanticId")),
        type=enum_value(src.text("type")),
    )


def _references(src: _Source, name: str) -> list:
    return _list(src, name, _reference)


def _level_type(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    return AasObject("LevelType", max=src.flag("max"), min=src.flag("min"), nom=src.flag("nom"), typ=src.flag("typ"))


def _value_list(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    pairs = _list(
        src,
        "valueReferencePairs",
        lambda p: AasObject("ValueReferencePair", value=p.text("value"), valueId=_reference(p.obj("valueId"))),
    )
    return AasObject("ValueList", valueReferencePairs=pairs)


def _data_specification_content(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    return AasObject(
        "DataSpecificationIec61360",
        dataType=enum_value(src.text("dataType")),
        definition=_list(src, "definition", _lang_string),
        levelType=_level_type(src.obj("levelType")),
        preferredName=_list(src, "preferredName", _lang_string),
        shortName=_list(src, "shortName", _lang_string),
        sourceOfDefinition=src.text("sourceOfDefinition"),
        symbol=src.text("symbol"),
        unit=src.text("unit"),
        unitId=_reference(src.obj("unitId")),
        value=src.text("value"),
        valueFormat=src.text("valueFormat"),
        valueList=_value_list(src.obj("valueList")),
    )


def _embedded_data_specification(src: _Source) -> AasObject:
    return AasObject(
        "EmbeddedDataSpecification",
        dataSpecification=_reference(src.obj("dataSpecification")),
        dataSpecificationContent=_data_specification_content(src.typed("dataSpecificationContent")),
    )


def _eds(src: _Source) -> list:
    return _list(src, "embeddedDataSpecifications", _embedded_data_specification)


def _extension(src: _Source) -> AasObject:
    return AasObject(
        "Extension",
        semanticId=_reference(src.obj("semanticId")),
        supplementalSemanticIds=_references(src, "supplementalSemanticIds"),
        name=src.text("name"),
        refersTo=_references(src, "refersTo"),
        value=src.text("value"),
        valueType=enum_value(src.text("valueType")),
    )


def _extensions(src: _Source) -> list:
    return _list(src, "extensions", _extension)


def _qualifier(src: _Source) -> AasObject:
    return AasObject(
        "Qualifier",
        semanticId=_reference(src.obj("semanticId")),
        supplementalSemanticIds=_references(src, "supplementalSemanticIds"),
        kind=enum_value(src.text("kind")) or "ConceptQualifier",  # Standardwert laut AAS-Metamodell
        type=src.text("type"),
        value=src.text("value"),
        valueId=_reference(src.obj("valueId")),
        valueType=enum_value(src.text("valueType")),
    )


def _specific_asset_id(src: _Source) -> AasObject:
    return AasObject(
        "SpecificAssetId",
        semanticId=_reference(src.obj("semanticId")),
        supplementalSemanticIds=_references(src, "supplementalSemanticIds"),
        externalSubjectId=_reference(src.obj("externalSubjectId")),
        name=src.text("name"),
        value=src.text("value"),
    )


def _administration(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    return AasObject(
        "AdministrativeInformation",
        creator=_reference(src.obj("creator")),
        revision=src.text("revision"),
        templateId=src.text("templateId"),
        version=src.text("version"),
        embeddedDataSpecifications=_eds(src),
    )


def _resource(src: Optional[_Source]) -> Optional[AasObject]:
    if src is None:
        return None
    return AasObject("Resource", contentType=src.text("contentType"), path=src.text("path"))


def _blob_value(value: Optional[str]) -> Optional[str]:
    """Blob-Werte werden als Standard-Base64 mit Padding ausgegeben."""
    if value is None:
        return None
    try:
        data = base64.b64decode("".join(value.split()), validate=False)
    except (binascii.Error, ValueError):
        data = value.encode("utf-8")
    return base64.b64encode(data).decode("ascii")


# --------------------------------------------------------------------------------------------------------------
# Submodel-Elemente
# --------------------------------------------------------------------------------------------------------------


def _head(src: _Source) -> dict:
    return {
        "embeddedDataSpecifications": _eds(src),
        "extensions": _extensions(src),
        "semanticId": _reference(src.obj("semanticId")),
        "supplementalSemanticIds": _references(src, "supplementalSemanticIds"),
    }


def _tail(src: _Source) -> dict:
    return {
        "qualifiers": _list(src, "qualifiers", _qualifier),
        "category": src.text("category"),
        "description": _list(src, "description", _lang_string),
        "displayName": _list(src, "displayName", _lang_string),
        "idShort": src.text("idShort"),
    }


def _elements(src: _Source, name: str) -> list:
    items = src.items(name)
    if isinstance(src, _XmlSource):
        items = _group_by_type(items)
    return [submodel_element(item) for item in items]


def _group_by_type(items: list[_Source]) -> list[_Source]:
    """Sortiert XML-Elemente stabil nach Typ, in der Reihenfolge des ersten Auftretens eines Typs.

    Diese Reihenfolge ist Teil des Antwortformats: z. B. stehen erst alle Collections, dann alle Properties.
    Das Frontend und gespeicherte idShortPath-Indizes ([0], [1], ...) verlassen sich darauf.
    """
    groups: dict[Optional[str], list[_Source]] = {}
    for item in items:
        groups.setdefault(item.model_type, []).append(item)
    return [item for group in groups.values() for item in group]


def _property(src: _Source) -> AasObject:
    return AasObject(
        "Property",
        **_head(src),
        value=src.text("value"),
        valueId=_reference(src.obj("valueId")),
        valueType=enum_value(src.text("valueType")),
        **_tail(src),
    )


def _multi_language_property(src: _Source) -> AasObject:
    return AasObject(
        "MultiLanguageProperty",
        **_head(src),
        value=_list(src, "value", _lang_string),
        valueId=_reference(src.obj("valueId")),
        **_tail(src),
    )


def _range(src: _Source) -> AasObject:
    return AasObject(
        "Range",
        **_head(src),
        max=src.text("max"),
        min=src.text("min"),
        valueType=enum_value(src.text("valueType")),
        **_tail(src),
    )


def _file(src: _Source) -> AasObject:
    return AasObject("File", contentType=src.text("contentType"), value=src.text("value"), **_head(src), **_tail(src))


def _blob(src: _Source) -> AasObject:
    return AasObject(
        "Blob",
        contentType=src.text("contentType"),
        value=_blob_value(src.text("value")),
        **_head(src),
        **_tail(src),
    )


def _reference_element(src: _Source) -> AasObject:
    return AasObject("ReferenceElement", **_head(src), **_tail(src), value=_reference(src.obj("value")))


def _relationship_element(src: _Source) -> AasObject:
    return AasObject(
        "RelationshipElement",
        **_head(src),
        **_tail(src),
        first=_reference(src.obj("first")),
        second=_reference(src.obj("second")),
    )


def _annotated_relationship_element(src: _Source) -> AasObject:
    return AasObject(
        "AnnotatedRelationshipElement",
        annotations=_elements(src, "annotations"),
        **_head(src),
        **_tail(src),
        first=_reference(src.obj("first")),
        second=_reference(src.obj("second")),
    )


def _entity(src: _Source) -> AasObject:
    return AasObject(
        "Entity",
        entityType=enum_value(src.text("entityType")),
        globalAssetId=src.text("globalAssetId"),
        specificAssetIds=_list(src, "specificAssetIds", _specific_asset_id),
        statements=_elements(src, "statements"),
        **_head(src),
        **_tail(src),
    )


def _submodel_element_collection(src: _Source) -> AasObject:
    return AasObject("SubmodelElementCollection", **_head(src), **_tail(src), value=_elements(src, "value"))


def _submodel_element_list(src: _Source) -> AasObject:
    return AasObject(
        "SubmodelElementList",
        **_head(src),
        **_tail(src),
        orderRelevant=src.flag("orderRelevant"),
        semanticIdListElement=_reference(src.obj("semanticIdListElement")),
        typeValueListElement=enum_value(src.text("typeValueListElement")),
        valueTypeListElement=enum_value(src.text("valueTypeListElement")),
        value=_elements(src, "value"),
    )


def _operation_variable(src: _Source) -> AasObject:
    value = src.typed("value")
    return AasObject("OperationVariable", value=None if value is None else submodel_element(value))


def _operation(src: _Source) -> AasObject:
    return AasObject(
        "Operation",
        **_head(src),
        **_tail(src),
        inoutputVariables=_list(src, "inoutputVariables", _operation_variable),
        inputVariables=_list(src, "inputVariables", _operation_variable),
        outputVariables=_list(src, "outputVariables", _operation_variable),
    )


def _capability(src: _Source) -> AasObject:
    return AasObject("Capability", **_head(src), **_tail(src))


def _basic_event_element(src: _Source) -> AasObject:
    return AasObject(
        "BasicEventElement",
        **_head(src),
        **_tail(src),
        direction=enum_value(src.text("direction")),
        lastUpdate=src.text("lastUpdate"),
        maxInterval=src.text("maxInterval"),
        messageBroker=_reference(src.obj("messageBroker")),
        messageTopic=src.text("messageTopic"),
        minInterval=src.text("minInterval"),
        observed=_reference(src.obj("observed")),
        state=enum_value(src.text("state")),
    )


_ELEMENT_BUILDERS: dict[str, Callable[[_Source], AasObject]] = {
    "Property": _property,
    "MultiLanguageProperty": _multi_language_property,
    "Range": _range,
    "File": _file,
    "Blob": _blob,
    "ReferenceElement": _reference_element,
    "RelationshipElement": _relationship_element,
    "AnnotatedRelationshipElement": _annotated_relationship_element,
    "Entity": _entity,
    "SubmodelElementCollection": _submodel_element_collection,
    "SubmodelElementList": _submodel_element_list,
    "Operation": _operation,
    "Capability": _capability,
    "BasicEventElement": _basic_event_element,
}


def submodel_element(src: _Source) -> AasObject:
    build = _ELEMENT_BUILDERS.get(src.model_type or "")
    if build is None:
        raise AasParseError(f"Unbekannter Submodel-Element-Typ: {src.model_type}")
    return build(src)


# --------------------------------------------------------------------------------------------------------------
# Identifiables
# --------------------------------------------------------------------------------------------------------------


def _asset_information(src: Optional[_Source]) -> AasObject:
    if src is None:
        src = _JsonSource({})
    return AasObject(
        "AssetInformation",
        assetKind=enum_value(src.text("assetKind")),
        assetType=src.text("assetType"),
        defaultThumbnail=_resource(src.obj("defaultThumbnail")),
        globalAssetId=src.text("globalAssetId"),
        specificAssetIds=_list(src, "specificAssetIds", _specific_asset_id),
    )


def _shell(src: _Source) -> AasObject:
    return AasObject(
        "AssetAdministrationShell",
        assetInformation=_asset_information(src.obj("assetInformation")),
        derivedFrom=_reference(src.obj("derivedFrom")),
        submodels=_references(src, "submodels"),
        embeddedDataSpecifications=_eds(src),
        extensions=_extensions(src),
        administration=_administration(src.obj("administration")),
        id=src.text("id"),
        category=src.text("category"),
        description=_list(src, "description", _lang_string),
        displayName=_list(src, "displayName", _lang_string),
        idShort=src.text("idShort"),
    )


def _submodel(src: _Source) -> AasObject:
    return AasObject(
        "Submodel",
        embeddedDataSpecifications=_eds(src),
        extensions=_extensions(src),
        kind=enum_value(src.text("kind")) or "Instance",  # Standardwert laut AAS-Metamodell
        semanticId=_reference(src.obj("semanticId")),
        supplementalSemanticIds=_references(src, "supplementalSemanticIds"),
        administration=_administration(src.obj("administration")),
        id=src.text("id"),
        qualifiers=_list(src, "qualifiers", _qualifier),
        category=src.text("category"),
        description=_list(src, "description", _lang_string),
        displayName=_list(src, "displayName", _lang_string),
        idShort=src.text("idShort"),
        submodelElements=_elements(src, "submodelElements"),
    )


class Environment:
    """Shells und Submodels eines AAS-Environments (ConceptDescriptions werden nicht benötigt)."""

    __slots__ = ("shells", "submodels")

    def __init__(self, shells: list[AasObject], submodels: list[AasObject]) -> None:
        self.shells = shells
        self.submodels = submodels


def _environment(src: _Source) -> Environment:
    return Environment(
        shells=[_shell(s) for s in src.items("assetAdministrationShells")],
        submodels=[_submodel(s) for s in src.items("submodels")],
    )


def _xml_parser() -> etree.XMLParser:
    """Neuer Parser je Aufruf (lxml-Parser sind nicht threadsicher).

    Keine Entitäten, kein DTD, kein Netzwerk (XXE). Kein ``huge_tree``: die Grenzen von libxml2 für
    Verschachtelungstiefe und Textlänge schützen vor präparierten Dateien.
    """
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_comments=True)


def parse_xml(data: bytes) -> Environment:
    """Liest ein AAS-3.0-Environment im XML-Format."""
    try:
        root = etree.fromstring(data, parser=_xml_parser())
    except etree.XMLSyntaxError as e:
        raise AasParseError(f"Kein gültiges XML: {e}") from e
    if _local(root.tag) != "environment":
        raise AasParseError(f"Unerwartetes Wurzelelement {_local(root.tag)}, erwartet environment")
    return _environment(_XmlSource(root))


def parse_json(data: Any) -> Environment:
    """Liest ein AAS-3.0-Environment im (spezifikationskonformen) JSON-Format, bereits mit json.loads geladen."""
    if not isinstance(data, dict) or not (
        "assetAdministrationShells" in data or "submodels" in data or "conceptDescriptions" in data
    ):
        raise AasParseError("JSON enthält kein AAS-Environment")
    return _environment(_JsonSource(data))


def walk(elements: Iterable[AasObject]) -> Iterable[AasObject]:
    """Alle Submodel-Elemente rekursiv (Collection, List, Entity, Annotationen, Operationsvariablen)."""
    for el in elements:
        yield el
        t = el.model_type
        if t in ("SubmodelElementCollection", "SubmodelElementList"):
            yield from walk(el["value"])
        elif t == "Entity":
            yield from walk(el["statements"])
        elif t == "AnnotatedRelationshipElement":
            yield from walk(el["annotations"])
        elif t == "Operation":
            for key in ("inputVariables", "outputVariables", "inoutputVariables"):
                yield from walk(v["value"] for v in el[key] if v["value"] is not None)
