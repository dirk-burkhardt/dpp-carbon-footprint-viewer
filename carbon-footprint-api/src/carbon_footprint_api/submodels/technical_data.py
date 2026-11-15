"""Parser für Technical Data (IDTA 02003): ZVEI 1.0/1.1, 1.2 und Generic Frame 2.0 bis 2.0.4."""

from __future__ import annotations

from typing import Optional

from ..aas.model import AasObject
from .models import Classification, FileRef, PropertyArea, TechnicalData, TechnicalProperty, TemplateInfo
from .query import children, lang_text, semantic_id, text
from .registry import detect
from .semantics import Semantics
from .structure import entries, named, one, value

# Platzhalter der Templates ohne eigene Bedeutung: Name kommt dann aus dem idShort
_PLACEHOLDERS = ("SemanticIdNotAvailable", "NON_EMPTY_VALUE", "NonstandardizedProperty", "SMT/General/Arbitrary")


def _generic(sid: Optional[str]) -> bool:
    return sid is None or any(p in sid for p in _PLACEHOLDERS)


def _file(element: Optional[AasObject]) -> Optional[FileRef]:
    if element is None:
        return None
    if element.model_type == "File":
        path = text(element)
        return FileRef(path=path, contentType=element.get("contentType")) if path else None
    # 2.0: ProductImages-Liste mit Collections, die eine Datei enthalten
    for child in children(element):
        found = _file(child)
        if found:
            return found
    return None


def _properties(element: AasObject, path: list[str], semantics: Semantics) -> list[TechnicalProperty]:
    result: list[TechnicalProperty] = []
    for i, child in enumerate(children(element)):
        t = child.model_type
        name = child.get("idShort") or f"[{i}]"
        if t in ("SubmodelElementCollection", "SubmodelElementList"):
            section = lang_text(child.get("displayName")) or name
            result.extend(_properties(child, [*path, section], semantics))
            continue
        if t not in ("Property", "MultiLanguageProperty", "Range", "File", "Blob"):
            continue
        sid = semantic_id(child)
        generic = _generic(sid)
        name = lang_text(child.get("displayName")) or (None if generic else semantics.name(child))
        prop = TechnicalProperty(
            path=path,
            idShort=child.get("idShort"),
            # Listeneinträge ohne idShort (Mehrfachwerte) tragen den Namen ihrer Liste
            name=(name or child.get("idShort") or "").strip() or (path[-1] if path else None),
            semanticId=None if generic else sid,
            modelType=t,
            valueType=child.get("valueType"),
            unit=None if generic else semantics.unit(child),
            definition=lang_text(child.get("description")) or (None if generic else semantics.definition(child)),
        )
        if t == "Range":
            prop.min, prop.max = child.get("min"), child.get("max")
            if prop.min is None and prop.max is None:
                continue
        elif t == "Blob":
            prop.value = child.get("contentType")
        else:
            prop.value = semantics.value_text(child, text(child))
            if prop.value is None:
                continue
        result.append(prop)
    return result


def _area(element: AasObject, fallback: str, semantics: Semantics) -> PropertyArea:
    return PropertyArea(
        name=lang_text(element.get("displayName")) or element.get("idShort") or fallback,
        properties=_properties(element, [], semantics),
    )


def parse_technical_data(
    submodel: AasObject, info: Optional[TemplateInfo] = None, semantics: Optional[Semantics] = None
) -> Optional[TechnicalData]:
    info = info or detect(submodel)
    if info.family != "technical-data":
        return None
    semantics = semantics or Semantics()
    result = TechnicalData(templateVersion=info.version or info.variant, submodelId=submodel.get("id"))
    general = one(submodel, ["GeneralInformation"])
    result.manufacturerName = value(general, ["ManufacturerName"])
    result.productDesignation = value(general, ["ManufacturerProductDesignation"])
    result.articleNumber = value(general, ["ManufacturerArticleNumber", "ManufacturerPartNumber"])
    result.orderCode = value(general, ["ManufacturerOrderCode"])
    result.logo = _file(one(general, ["CompanyLogo", "ManufacturerLogo"]))
    images = [_file(e) for e in named(general, ["ProductImage", "ProductImages"])]
    for image_list in named(general, ["ProductImages"]):
        images = [_file(e) for e in children(image_list)] or images
    result.productImages = [i for i in images if i is not None]

    for _, item in entries(submodel, ["ProductClassifications"], []):
        result.classifications.append(_classification(item))
    for holder in named(submodel, ["ProductClassifications"]):
        if holder.model_type == "SubmodelElementCollection":
            for _, item in entries(holder, [], ["ProductClassificationItem"]):
                result.classifications.append(_classification(item))
    result.classifications = [c for c in result.classifications if c.classId or c.system]

    for i, (_, area) in enumerate(entries(submodel, ["TechnicalPropertyAreas"], ["TechnicalProperties"])):
        result.areas.append(_area(area, f"Bereich {i + 1}", semantics))
    result.areas = [a for a in result.areas if a.properties]
    for i, (_, desc) in enumerate(entries(submodel, ["SpecificDescriptions"], [])):
        result.specificDescriptions.append(_area(desc, f"Beschreibung {i + 1}", semantics))
    result.specificDescriptions = [a for a in result.specificDescriptions if a.properties]

    further = one(submodel, ["FurtherInformation"])
    result.textStatement = value(further, ["TextStatement"])
    result.validDate = value(further, ["ValidDate"])
    return result


def _classification(item: AasObject) -> Classification:
    return Classification(
        system=value(item, ["ClassificationSystem", "ProductClassificationSystem"]),
        version=value(item, ["ClassificationSystemVersion", "SystemVersion"]),
        url=value(item, ["ClassificationSystemUrl"]),
        classId=value(item, ["ProductClassId", "ProductClass"]),
        className=value(item, ["ProductClassName", "ProductClassCodedName"]),
    )
