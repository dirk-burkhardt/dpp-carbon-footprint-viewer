"""Fachliche Endpunkte: versionsunabhängig aufbereitete Daten der IDTA-Submodels."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Optional

from fastapi import APIRouter, Path

from ...services import ProductService
from ...submodels import catalog
from ...submodels.models import (
    CarbonFootprintResult,
    HandoverDocumentation,
    Indicators,
    MaintenanceInstructions,
    Nameplate,
    ProductDetails,
    ProductTree,
    TechnicalData,
    TemplateInfo,
)
from ..deps import Repository, decode_id
from ..errors import ERROR_RESPONSE, ApiError

router = APIRouter(prefix="/products", tags=["Products"])

AAS_ID = Path(description="Id or globalAssetId of the Asset Administration Shell (UTF8-BASE64-URL-encoded)")
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: ERROR_RESPONSE}


def _shell_id(repo: Repository, value: str) -> str:
    shell_id = decode_id(value, "aasIdentifier")
    if not repo.has_shell(shell_id):
        raise ApiError(HTTPStatus.NOT_FOUND, "Asset Administration Shell not found")
    return shell_id


@router.get("/submodel-templates", description="Supported IDTA submodel templates and versions")
def supported_templates() -> dict[str, Any]:
    data = catalog()
    return {
        "repository": data["repository"],
        "families": [
            {k: f[k] for k in ("key", "name", "idta", "parsing", "knownVersions")}
            | {"versions": sorted(set(f["semanticIds"].values()))}
            for f in data["families"]
        ],
    }


@router.get(
    "/{aasIdentifier}/templates",
    description="Detected IDTA template, version and variant of every submodel of a shell",
    responses=NOT_FOUND,
    response_model=list[TemplateInfo],
)
def templates(repo: Repository, aasIdentifier: str = AAS_ID) -> list[TemplateInfo]:
    return ProductService(repo).templates(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/carbon-footprint",
    description="Normalized carbon footprints of all template versions with a summary per calculation method",
    responses=NOT_FOUND,
    response_model=CarbonFootprintResult,
)
def carbon_footprint(repo: Repository, aasIdentifier: str = AAS_ID) -> CarbonFootprintResult:
    return ProductService(repo).carbon_footprint(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/indicators",
    description="Reference quantities from Technical Data in SI units (mass in kg, power in W, service life in "
    "years, dimensions in m) with their source, e.g. to state CO2eq per kg or per watt",
    responses=NOT_FOUND,
    response_model=Indicators,
)
def indicators(repo: Repository, aasIdentifier: str = AAS_ID) -> Indicators:
    return ProductService(repo).indicators(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/nameplate",
    description="Manufacturer and address from the nameplate (null if the shell has none)",
    responses=NOT_FOUND,
    response_model=Optional[Nameplate],
)
def nameplate(repo: Repository, aasIdentifier: str = AAS_ID) -> Optional[Nameplate]:
    return ProductService(repo).nameplate(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/technical-data",
    description="Technical Data (all versions) with names and units from the concept descriptions",
    responses=NOT_FOUND,
    response_model=list[TechnicalData],
)
def technical_data(repo: Repository, aasIdentifier: str = AAS_ID) -> list[TechnicalData]:
    return ProductService(repo).technical_data(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/documentation",
    description="Documents from Handover Documentation (VDI 2770 1.0, IDTA 02004 1.2 and 2.0)",
    responses=NOT_FOUND,
    response_model=list[HandoverDocumentation],
)
def documentation(repo: Repository, aasIdentifier: str = AAS_ID) -> list[HandoverDocumentation]:
    return ProductService(repo).documentation(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/maintenance",
    description="Maintenance Instructions: intervals, steps, tools, consumables and spare parts",
    responses=NOT_FOUND,
    response_model=list[MaintenanceInstructions],
)
def maintenance(repo: Repository, aasIdentifier: str = AAS_ID) -> list[MaintenanceInstructions]:
    return ProductService(repo).maintenance(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/details",
    description="All evaluated submodels of a shell: templates, nameplate, technical data, documents, maintenance",
    responses=NOT_FOUND,
    response_model=ProductDetails,
)
def details(repo: Repository, aasIdentifier: str = AAS_ID) -> ProductDetails:
    return ProductService(repo).details(_shell_id(repo, aasIdentifier))


@router.get(
    "/{aasIdentifier}/tree",
    description="Product tree across all shells (Hierarchical Structures) with nameplate and carbon footprint",
    responses=NOT_FOUND,
    response_model=ProductTree,
)
def product_tree(repo: Repository, aasIdentifier: str = AAS_ID) -> ProductTree:
    tree = ProductService(repo).product_tree(_shell_id(repo, aasIdentifier))
    if tree is None:  # pragma: no cover - Shell wurde oben geprüft
        raise ApiError(HTTPStatus.NOT_FOUND, "Asset Administration Shell not found")
    return tree
