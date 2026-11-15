"""Zusätzliche Endpunkte mit nicht codierten IDs."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Path

from ..deps import Repository
from ..errors import ERROR_RESPONSE, ApiError

router = APIRouter(tags=["Assets"])

RAW_AAS_ID = Path(description="The Asset Administration Shell’s unique id or globalAssetId (NOT encoded)")


@router.get("/asset/all", description="Get the IDs and idShorts of all available assets")
def available_assets(repo: Repository):
    return repo.available_shell_ids()


@router.get(
    "/asset/{aasIdentifier:path}/submodel/all",
    description="Get the IDs of all submodels of an asset",
    responses={404: ERROR_RESPONSE},
)
def available_submodels(repo: Repository, aasIdentifier: str = RAW_AAS_ID):
    ids = repo.available_submodel_ids(aasIdentifier)
    if ids is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Asset Administration Shell not found")
    return ids


@router.get(
    "/asset/{aasIdentifier:path}/submodel/{submodelId:path}",
    description="Get the submodel of an AssetAdministrationShell by the shells global ID and the submodels ID.",
    responses={404: ERROR_RESPONSE},
)
def get_asset_submodel(
    repo: Repository,
    aasIdentifier: str = RAW_AAS_ID,
    submodelId: str = Path(description="The Submodel’s unique id (NOT encoded)"),
):
    submodel = repo.get_submodel(aasIdentifier, submodelId)
    if submodel is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Submodel not found")
    return submodel
