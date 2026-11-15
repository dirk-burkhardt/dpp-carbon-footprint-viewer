"""Endpunkte nach AAS-Repository-Spezifikation (Base64-URL-codierte IDs)."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Path, Response

from ..deps import Repository, decode_id
from ..errors import ERROR_RESPONSE, ApiError
from ..responses import file_response

router = APIRouter(tags=["Asset Administration Shells"])

AAS_ID = Path(description="The Asset Administration Shell’s unique id (UTF8-BASE64-URL-encoded)")
SUBMODEL_ID = Path(description="The Submodel’s unique id (UTF8-BASE64-URL-encoded)")
# idShorts dürfen "/" enthalten (als %2F codiert), daher der path-Konverter.
# Die Attachment-Route muss vor der Element-Route registriert sein.
ID_SHORT_PATH = Path(description="idShortPath with ./[]-notation")
FILE_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"description": "Datei", "content": {"application/octet-stream": {}}},
    404: ERROR_RESPONSE,
}


def _require_submodel(repo: Repository, aas_id: str, submodel_id: str) -> None:
    if not repo.has_shell(aas_id):
        raise ApiError(HTTPStatus.NOT_FOUND, "Asset Administration Shell not found")
    if not repo.has_submodel(aas_id, submodel_id):
        raise ApiError(HTTPStatus.NOT_FOUND, "Submodel not found")


@router.get(
    "/concept-descriptions/{cdIdentifier}",
    description="Returns a specific Concept Description from the loaded files",
    responses={404: ERROR_RESPONSE},
)
def get_concept_description(repo: Repository, cdIdentifier: str = Path(description="UTF8-BASE64-URL-encoded id")):
    cd = repo.get_concept_description(decode_id(cdIdentifier, "cdIdentifier"))
    if cd is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Concept Description not found")
    return cd


@router.get("/shell-descriptors", description="Returns all Asset Administration Shell Descriptors")
def get_shell_descriptors(repo: Repository):
    return {"result": repo.shell_descriptors(), "paging_metadata": {"cursor": None}}


@router.get(
    "/shells/{aasIdentifier}",
    description="Returns a specific Asset Administration Shell",
    responses={404: ERROR_RESPONSE},
)
def get_shell(repo: Repository, aasIdentifier: str = AAS_ID):
    shell = repo.get_shell(decode_id(aasIdentifier, "aasIdentifier"))
    if shell is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Asset Administration Shell not found")
    return shell


@router.get(
    "/shells/{aasIdentifier}/submodel-refs",
    description="Returns the Submodel refs of a shell (result is null for an unknown shell)",
)
def get_submodel_refs(repo: Repository, aasIdentifier: str = AAS_ID):
    refs = repo.submodel_refs(decode_id(aasIdentifier, "aasIdentifier"))
    return {"result": refs, "paging_metadata": {"cursor": None}}


@router.get(
    "/shells/{aasIdentifier}/asset-information/thumbnail",
    description="Returns the thumbnail file",
    response_class=Response,
    responses=FILE_RESPONSES,
)
def get_thumbnail(repo: Repository, aasIdentifier: str = AAS_ID):
    thumbnail = repo.get_thumbnail(decode_id(aasIdentifier, "aasIdentifier"))
    if thumbnail is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Thumbnail not found")
    return file_response(*thumbnail)


@router.get(
    "/shells/{aasIdentifier}/submodels/{submodelIdentifier}",
    description="Returns the Submodel.",
    responses={404: ERROR_RESPONSE},
)
def get_shell_submodel(repo: Repository, aasIdentifier: str = AAS_ID, submodelIdentifier: str = SUBMODEL_ID):
    aas_id = decode_id(aasIdentifier, "aasIdentifier")
    submodel_id = decode_id(submodelIdentifier, "submodelIdentifier")
    _require_submodel(repo, aas_id, submodel_id)
    return repo.get_submodel(aas_id, submodel_id)


@router.get(
    "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath:path}/attachment",
    description="Get the Submodel Element Attachment of a specific idShortPath.",
    response_class=Response,
    responses=FILE_RESPONSES,
)
def get_shell_submodel_element_attachment(
    repo: Repository,
    aasIdentifier: str = AAS_ID,
    submodelIdentifier: str = SUBMODEL_ID,
    idShortPath: str = ID_SHORT_PATH,
):
    aas_id = decode_id(aasIdentifier, "aasIdentifier")
    submodel_id = decode_id(submodelIdentifier, "submodelIdentifier")
    _require_submodel(repo, aas_id, submodel_id)
    attachment = repo.get_submodel_element_attachment(aas_id, submodel_id, idShortPath)
    if attachment is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Attachment not found")
    return file_response(*attachment)


@router.get(
    "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath:path}",
    description="Get the Submodel Element of a specific idShortPath. "
    "An unknown idShortPath returns 200 with an empty body.",
    responses={404: ERROR_RESPONSE},
)
def get_shell_submodel_element(
    repo: Repository,
    aasIdentifier: str = AAS_ID,
    submodelIdentifier: str = SUBMODEL_ID,
    idShortPath: str = ID_SHORT_PATH,
):
    aas_id = decode_id(aasIdentifier, "aasIdentifier")
    submodel_id = decode_id(submodelIdentifier, "submodelIdentifier")
    _require_submodel(repo, aas_id, submodel_id)
    element = repo.get_submodel_element(aas_id, submodel_id, idShortPath)
    if element is None:
        return Response(status_code=HTTPStatus.OK)
    return element
