"""Erkennung der IDTA-Template-Familie und -Version eines Submodels."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any, Optional

from ..aas.model import AasObject, walk
from .models import TemplateInfo
from .query import find, normalize_semantic_id, semantic_id, semantic_ids

CF_PRODUCT_LIST = "https://admin-shell.io/idta/CarbonFootprint/ProductCarbonFootprints/1/0"
CF_PERFORMANCE_CLASS = "urn:samm:io.admin-shell.idta.batterypass.carbon_footprint:1.0.0#performanceClass"


@dataclass(frozen=True)
class Family:
    key: str
    name: str
    idta: str
    folders: tuple[str, ...]
    parsing: str
    semantic_ids: dict[str, str]
    known_versions: tuple[str, ...]
    without_json_template: tuple[str, ...] = field(default=())


@cache
def catalog() -> dict[str, Any]:
    """Inhalt von ``known_templates.json``."""
    raw = resources.files(__package__).joinpath("known_templates.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    return data


@cache
def families() -> tuple[Family, ...]:
    return tuple(
        Family(
            key=f["key"],
            name=f["name"],
            idta=f["idta"],
            folders=tuple(f["folders"]),
            parsing=f["parsing"],
            semantic_ids=dict(f["semanticIds"]),
            known_versions=tuple(f["knownVersions"]),
            without_json_template=tuple(f.get("withoutJsonTemplate", ())),
        )
        for f in catalog()["families"]
    )


def family(key: str) -> Family:
    return next(f for f in families() if f.key == key)


def _lookup(submodel: AasObject) -> tuple[Optional[Family], Optional[str]]:
    """Zuerst die SemanticId genau (bei IRDIs unterscheidet der Versionsanhang die Template-Version), dann
    normalisiert, zuletzt die zusätzlichen SemanticIds."""
    primary = semantic_id(submodel)
    candidates = [primary.strip()] if primary else []
    candidates += semantic_ids(submodel)
    for sid in candidates:
        for fam in families():
            if sid in fam.semantic_ids:
                return fam, fam.semantic_ids[sid]
            for known, version in fam.semantic_ids.items():
                if normalize_semantic_id(known) == sid:
                    return fam, version
    return None, None


def has_values(submodel: AasObject) -> bool:
    """Enthält das Submodel verwertbare Werte (sonst ist es eine leere Template-Kopie)?"""
    if submodel.get("kind") == "Template":
        return False
    for el in walk(submodel.get("submodelElements") or []):
        t = el.model_type
        if t == "Property" and el.get("value") not in (None, ""):
            return True
        if t == "MultiLanguageProperty" and any(v.get("text") for v in el.get("value") or []):
            return True
        if t == "Entity" and el.get("globalAssetId"):
            return True
    return False


def detect(submodel: AasObject) -> TemplateInfo:
    """Familie, Version und Variante eines Submodels; unbekannte Submodels mit ``family=None``."""
    fam, version = _lookup(submodel)
    info = TemplateInfo(
        submodelId=submodel.get("id"),
        idShort=submodel.get("idShort"),
        semanticId=semantic_id(submodel),
        family=None,
        isTemplate=not has_values(submodel),
    )
    if fam is None and not semantic_ids(submodel):
        # Ältere Dateien ohne SemanticId: Erkennung über den idShort (Carbon Footprint wie bisher in der API)
        id_short = submodel.get("idShort") or ""
        for prefix, target in catalog().get("idShortFallback", {}).items():
            if not prefix.startswith("_") and id_short.startswith(prefix):
                fam, version = family(target[0]), target[1]
                info.variant = "ohne SemanticId"
                break
    if fam is None:
        non_idta = catalog().get("nonIdtaSemanticIds", {})
        for sid in semantic_ids(submodel):
            if sid in non_idta:
                info.family = non_idta[sid]
                info.variant = "nicht IDTA"
                info.parsing = "full"
        return info
    info.family = fam.key
    info.name = fam.name
    info.idta = fam.idta
    info.version = version
    info.parsing = "full" if fam.parsing == "full" else "detect"
    if fam.key == "carbon-footprint" and version == "1.0":
        if find(submodel, [CF_PRODUCT_LIST], ["ProductCarbonFootprints"]) is None:
            info.variant = "1.0-Entwurf"
        elif any(CF_PERFORMANCE_CLASS in semantic_ids(el) for el in walk(submodel["submodelElements"])):
            bat = family("battery-carbon-footprint")
            info.variant = f"{bat.idta} ({bat.name})"
    return info
