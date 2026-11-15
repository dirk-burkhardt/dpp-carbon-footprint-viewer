"""Hilfsfunktionen für Shells und Submodels (Carbon-Footprint-Erkennung, globalAssetId-Ketten).

Die Funktionen arbeiten auf den :class:`~carbon_footprint_api.aas_model.AasObject`-Dicts des Parsers.
"""

from __future__ import annotations

import logging
from typing import Optional

from .model import AasObject

logger = logging.getLogger(__name__)

# (globalAssetId, Kette der idShorts bis zur Fundstelle)
IdChain = tuple[str, tuple[Optional[str], ...]]


def is_carbon_footprint(submodel: AasObject) -> bool:
    """Prüft, ob ein Submodel einen Carbon Footprint darstellt."""
    return submodel["idShort"] == "CarbonFootprint"


def get_only_key_value(reference: AasObject, check_key_type: Optional[str] = None) -> str:
    """Wert des einzigen Keys einer Referenz.

    :raises ValueError: wenn die Referenz nicht genau einen Key (vom Typ ``check_key_type``) hat
    """
    keys = reference["keys"]
    if len(keys) != 1 or (check_key_type is not None and keys[0]["type"] != check_key_type):
        raise ValueError(f"Falscher Key: genau ein Key vom Typ {check_key_type} erwartet.")
    return keys[0]["value"]


def get_semantic_id(submodel: AasObject) -> str:
    return get_only_key_value(submodel["semanticId"], "GlobalReference")


def get_submodel_id(submodel_ref: AasObject) -> str:
    return get_only_key_value(submodel_ref, "Submodel")


def get_global_asset_ids(submodel: AasObject) -> set[str]:
    """Alle globalAssetIds, auf die im Submodel verwiesen wird."""
    result: set[str] = set()
    for element in submodel["submodelElements"]:
        chains: list[IdChain] = []
        _add_chains(chains, element, ())
        result.update(asset_id for asset_id, _ in chains)
    return result


def get_global_asset_id_chains(submodel: AasObject) -> list[IdChain]:
    """Alle globalAssetIds mit der idShort-Kette, über die sie erreicht werden."""
    chains: list[IdChain] = []
    for element in submodel["submodelElements"]:
        _add_chains(chains, element, (element["idShort"],))
    return chains


def _add_chains(chains: list[IdChain], element: AasObject, chain: tuple[Optional[str], ...]) -> None:
    t = element.model_type
    if t == "Entity" and element["entityType"] in ("CoManagedEntity", "SelfManagedEntity"):
        for sub in element["statements"]:
            _add_chains(chains, sub, (*chain, sub["idShort"]))
        asset_id = element["globalAssetId"]
        if asset_id is not None:
            chains.append((asset_id, chain))
        elif element["entityType"] == "SelfManagedEntity":
            logger.warning("SelfManagedEntity %s hat keine globalAssetId.", element["idShort"])
    if t == "ReferenceElement" and element["value"] is not None:
        _add_reference_values(chains, element["value"], chain)
    if t in ("SubmodelElementCollection", "SubmodelElementList"):
        for sub in element["value"]:
            _add_chains(chains, sub, (*chain, sub["idShort"]))
    if t == "RelationshipElement":
        for ref in (element["first"], element["second"]):
            if ref is not None:
                _add_reference_values(chains, ref, chain)


def _add_reference_values(chains: list[IdChain], reference: AasObject, chain: tuple[Optional[str], ...]) -> None:
    for key in reference["keys"]:
        if key["type"] == "GlobalReference":
            chains.append((key["value"], chain))
