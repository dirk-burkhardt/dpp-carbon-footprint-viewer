"""Parser für Hierarchical Structures enabling Bills of Material (IDTA 02011) 1.0 und 1.1.x."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..aas.model import AasObject
from .query import children, find, find_all, number, text
from .registry import detect

logger = logging.getLogger(__name__)

HS = "https://admin-shell.io/idta/HierarchicalStructures/"
ENTRY_NODE = (HS + "EntryNode/1/0",)
NODE = (HS + "Node/1/0",)
HAS_PART = (HS + "HasPart/1/0",)
IS_PART_OF = (HS + "IsPartOf/1/0",)
ARCHE_TYPE = (HS + "ArcheType/1/0",)
BULK_COUNT = (HS + "BulkCount/1/0",)
ARCHE_TYPES = ("OneDown", "OneUp", "Full")


@dataclass
class Relation:
    parent: AasObject
    child: AasObject
    relation: AasObject


@dataclass
class Hierarchy:
    submodel: AasObject
    version: Optional[str]
    arche_type: str
    entry: AasObject
    relations: list[Relation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def entry_asset_id(self) -> Optional[str]:
        return self.entry.get("globalAssetId")


def bulk_count(entity: AasObject) -> Optional[float]:
    return number(find(entity, BULK_COUNT, ("BulkCount",)))


def _resolve(submodel: AasObject, reference: Optional[AasObject]) -> Optional[AasObject]:
    """Löst eine ModelReference (Submodel, Entity, Entity, …) über die idShorts auf."""
    if not reference:
        return None
    keys = reference.get("keys") or []
    if not keys or keys[0].get("type") != "Submodel" or keys[0].get("value") != submodel.get("id"):
        return None
    current: Optional[AasObject] = submodel
    for key in keys[1:]:
        if current is None:
            return None
        current = next((c for c in children(current) if c.get("idShort") == key.get("value")), None)
    return current


def parse_hierarchy(submodel: AasObject) -> Optional[Hierarchy]:
    """Struktur eines Hierarchical-Structures-Submodels; ``None`` bei fremden oder leeren Submodels."""
    info = detect(submodel)
    if info.family != "hierarchical-structures":
        return None
    entry = find(submodel, ENTRY_NODE, ("EntryNode",))
    if entry is None or not entry.get("globalAssetId"):
        return None  # leere Template-Kopie
    arche = text(find(submodel, ARCHE_TYPE, ("ArcheType",))) or "Full"
    result = Hierarchy(submodel=submodel, version=info.version, arche_type=arche, entry=entry)
    if arche not in ARCHE_TYPES:
        result.warnings.append(f"Unbekannter ArcheType '{arche}', behandelt als Full")
        result.arche_type = "Full"
    reverse = result.arche_type == "OneUp"
    nodes = [entry]
    while nodes:
        node = nodes.pop()
        nodes.extend(find_all(node, NODE, ("Node",)))
        for rel in find_all(node, IS_PART_OF if reverse else HAS_PART, ("IsPartOf",) if reverse else ("HasPart",)):
            first, second = _resolve(submodel, rel.get("first")), _resolve(submodel, rel.get("second"))
            parent, child = (second, first) if reverse else (first, second)
            if parent is None or child is None:
                result.warnings.append(f"Relation {rel.get('idShort')} verweist auf unbekannte Knoten")
                continue
            result.relations.append(Relation(parent=parent, child=child, relation=rel))
    return result
