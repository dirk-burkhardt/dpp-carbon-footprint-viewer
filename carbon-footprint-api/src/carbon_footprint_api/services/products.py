"""Fachliche Sicht auf die Shells: erkannte Templates, Carbon Footprint, Typenschild und Produktbaum."""

from __future__ import annotations

from typing import Optional

from ..aas.model import AasObject
from ..repository import AssetRepository
from ..submodels import (
    Hierarchy,
    Semantics,
    derive_indicators,
    detect,
    parse_carbon_footprint,
    parse_handover_documentation,
    parse_hierarchy,
    parse_maintenance_instructions,
    parse_nameplate,
    parse_technical_data,
    summarize,
)
from ..submodels.hierarchy import bulk_count
from ..submodels.models import (
    CarbonFootprintResult,
    HandoverDocumentation,
    Indicators,
    LangText,
    MaintenanceInstructions,
    Nameplate,
    ProductDetails,
    ProductNode,
    ProductTree,
    TechnicalData,
    TemplateInfo,
)

MAX_DEPTH = 64

# Kinder je globalAssetId: (Entity des Kindes, Relation)
Connections = dict[str, list[tuple[AasObject, AasObject]]]


class ProductService:
    def __init__(self, repository: AssetRepository) -> None:
        self._repo = repository

    def _submodels(self, shell_id: str) -> list[AasObject]:
        shell = self._repo.get_shell(shell_id)
        if shell is None:
            return []
        ids = self._repo.available_submodel_ids(shell["id"]) or []
        return [sm for sm in (self._repo.get_submodel(shell["id"], i) for i in ids) if sm is not None]

    def templates(self, shell_id: str) -> list[TemplateInfo]:
        return [detect(sm) for sm in self._submodels(shell_id)]

    def _semantics(self) -> Semantics:
        return Semantics(getattr(self._repo, "get_concept_description", None))

    def technical_data(self, shell_id: str) -> list[TechnicalData]:
        semantics = self._semantics()
        found = (parse_technical_data(sm, detect(sm), semantics) for sm in self._filled(shell_id))
        return [t for t in found if t is not None]

    def indicators(self, shell_id: str) -> Indicators:
        return derive_indicators(self.technical_data(shell_id))

    def documentation(self, shell_id: str) -> list[HandoverDocumentation]:
        found = (parse_handover_documentation(sm) for sm in self._filled(shell_id))
        return [d for d in found if d is not None]

    def maintenance(self, shell_id: str) -> list[MaintenanceInstructions]:
        found = (parse_maintenance_instructions(sm) for sm in self._filled(shell_id))
        return [m for m in found if m is not None]

    def details(self, shell_id: str) -> ProductDetails:
        return ProductDetails(
            templates=self.templates(shell_id),
            nameplate=self.nameplate(shell_id),
            technicalData=self.technical_data(shell_id),
            documentation=self.documentation(shell_id),
            maintenance=self.maintenance(shell_id),
        )

    def _filled(self, shell_id: str) -> list[AasObject]:
        """Submodels ohne leere Template-Kopien."""
        return [sm for sm in self._submodels(shell_id) if not detect(sm).isTemplate]

    def carbon_footprint(self, shell_id: str) -> CarbonFootprintResult:
        result = CarbonFootprintResult()
        for sm in self._submodels(shell_id):
            info = detect(sm)
            if info.family != "carbon-footprint" or info.isTemplate:
                continue
            result.templates.append(info)
            result.footprints.extend(parse_carbon_footprint(sm, info))
        result.summary = summarize(result.footprints)
        return result

    def nameplate(self, shell_id: str) -> Optional[Nameplate]:
        plates = [p for p in (parse_nameplate(sm) for sm in self._submodels(shell_id)) if p is not None]
        # IDTA-Typenschild vor HSU-Variante, das mit Herstellernamen zuerst
        plates.sort(key=lambda p: (p.manufacturerName is None, p.templateVersion == "nicht IDTA"))
        return plates[0] if plates else None

    def hierarchy(self, shell_id: str) -> Optional[Hierarchy]:
        shell = self._repo.get_shell(shell_id)
        if shell is None:
            return None
        found = [h for h in (parse_hierarchy(sm) for sm in self._submodels(shell_id)) if h is not None]
        own = shell["assetInformation"]["globalAssetId"]
        found.sort(key=lambda h: (h.entry_asset_id != own, not h.relations))
        return found[0] if found else None

    # ----------------------------------------------------------------------------------------------------------

    def product_tree(self, shell_id: str) -> Optional[ProductTree]:
        shell = self._repo.get_shell(shell_id)
        if shell is None:
            return None
        hierarchy = self.hierarchy(shell_id)
        root_id = shell["assetInformation"]["globalAssetId"] or shell["id"]
        tree = ProductTree(root=ProductNode(globalAssetId=root_id))
        connections: Connections = {}
        loaded: set[str] = set()
        if hierarchy is not None:
            tree.archeType = hierarchy.arche_type
            tree.hierarchyVersion = hierarchy.version
            tree.warnings.extend(hierarchy.warnings)
            if hierarchy.entry_asset_id and hierarchy.entry_asset_id != root_id:
                tree.warnings.append("EntryNode verweist nicht auf das Asset der Shell")
                root_id = hierarchy.entry_asset_id
            self._merge(connections, hierarchy)
        loaded.add(root_id)
        tree.root = self._node(root_id, None, None, connections, loaded, (), tree)
        return tree

    @staticmethod
    def _merge(connections: Connections, hierarchy: Hierarchy) -> None:
        local: Connections = {}
        for rel in hierarchy.relations:
            parent_id = rel.parent.get("globalAssetId")
            if parent_id and rel.child.get("globalAssetId"):
                local.setdefault(parent_id, []).append((rel.child, rel.relation))
        for parent_id, kids in local.items():
            connections.setdefault(parent_id, kids)  # bereits bekannte Verbindungen haben Vorrang

    def _node(
        self,
        asset_id: str,
        entity: Optional[AasObject],
        relation: Optional[AasObject],
        connections: Connections,
        loaded: set[str],
        path: tuple[str, ...],
        tree: ProductTree,
    ) -> ProductNode:
        tree.nodeCount += 1
        node = ProductNode(globalAssetId=asset_id)
        if entity is not None:
            node.entityIdShort = entity.get("idShort")
            node.bulkCount = bulk_count(entity)
        if relation is not None:
            node.relationIdShort = relation.get("idShort")
        shell = self._repo.get_shell(asset_id)
        if shell is None:
            node.warnings.append("Keine Shell zu dieser globalAssetId geladen")
        else:
            node.shellId = shell["id"]
            node.idShort = shell["idShort"]
            node.displayName = _lang(shell["displayName"])
            node.description = _lang(shell["description"])
            node.nameplate = self.nameplate(shell["id"])
            cf = self.carbon_footprint(shell["id"])
            node.carbonFootprint = cf if cf.footprints else None
            if asset_id not in loaded:
                loaded.add(asset_id)
                sub = self.hierarchy(shell["id"])
                if sub is not None:
                    self._merge(connections, sub)
        if asset_id in path:
            node.warnings.append("Zyklus in der Stückliste, Unterbaum nicht weiter verfolgt")
            return node
        if len(path) >= MAX_DEPTH:
            node.warnings.append("Maximale Tiefe erreicht")
            return node
        for child, rel in connections.get(asset_id, []):
            node.children.append(
                self._node(child["globalAssetId"], child, rel, connections, loaded, (*path, asset_id), tree)
            )
        return node


def _lang(values: list) -> list[LangText]:
    return [LangText(language=v.get("language"), text=v.get("text")) for v in values or []]
