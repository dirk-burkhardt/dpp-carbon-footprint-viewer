"""Laden von Shells aus einer URL."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Path, Response

from ...services import ExternalDownloadError
from ..deps import AppSettings, External, decode_id
from ..errors import ERROR_RESPONSE, ApiError

router = APIRouter(tags=["External Shells"])


@router.get(
    "/external-shells/{url}",
    description="Returns all Asset Administration Shells contained in an environment from a url. "
    "Only public http(s) addresses are allowed; loaded shells never replace existing ones.",
    responses={
        204: {"description": "Remote server did not answer with 200"},
        403: ERROR_RESPONSE,
        404: ERROR_RESPONSE,
        422: ERROR_RESPONSE,
        502: ERROR_RESPONSE,
        504: ERROR_RESPONSE,
    },
)
async def get_external_shells(
    settings: AppSettings,
    service: External,
    url: str = Path(description="url where the shell can be downloaded (UTF8-BASE64-URL-encoded)"),
):
    if not settings.external_shells_enabled:
        raise ApiError(HTTPStatus.FORBIDDEN, "Laden von URLs ist deaktiviert")
    try:
        shells = await service.load(decode_id(url, "url"))
    except ExternalDownloadError as e:
        raise ApiError(e.status, e.message) from None
    if shells is None:
        return Response(status_code=HTTPStatus.NO_CONTENT)
    return shells
