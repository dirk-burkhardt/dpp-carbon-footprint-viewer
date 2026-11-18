"""Temporary uploads of AAS/AASX files."""

from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Optional

import anyio
from fastapi import APIRouter, Path, Query, Request, Response

from ...aas import AasObject
from ...services import Upload, UploadError
from ..deps import AppSettings, Uploads
from ..errors import ERROR_RESPONSE, ApiError

router = APIRouter(tags=["Uploads"])

UPLOAD_ID_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _describe(upload: Upload, shells: list[AasObject]) -> dict[str, Any]:
    return {
        "id": upload.token,
        "filename": upload.filename,
        "size": upload.size,
        "createdAt": _timestamp(upload.created),
        "expiresAt": _timestamp(upload.expires),
        "shells": shells,
    }


def _check_enabled(settings: AppSettings) -> None:
    if not settings.uploads_enabled:
        raise ApiError(HTTPStatus.FORBIDDEN, "Hochladen ist deaktiviert")


@router.get("/uploads", description="Whether uploads are possible, the maximum file size and how long they are kept")
def get_upload_limits(settings: AppSettings, service: Uploads):
    return {
        "enabled": settings.uploads_enabled,
        "maxBytes": service.max_bytes,
        "ttlSeconds": int(service.ttl_seconds),
    }


@router.post(
    "/uploads",
    status_code=HTTPStatus.CREATED,
    description="Uploads an .aasx, .aas.json or .aas.xml file as request body (application/octet-stream). "
    "The shells are kept in memory only and deleted after the configured time or on a restart of the API. "
    "Uploaded shells never replace existing ones. Returns the upload with its id and the contained shells.",
    responses={403: ERROR_RESPONSE, 413: ERROR_RESPONSE, 422: ERROR_RESPONSE},
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def post_upload(
    request: Request,
    settings: AppSettings,
    service: Uploads,
    filename: Optional[str] = Query(None, description="Original file name, its ending determines the format"),
):
    _check_enabled(settings)
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > service.max_bytes:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Datei ist zu groß")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > service.max_bytes:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Datei ist zu groß")
        chunks.append(chunk)
    data = b"".join(chunks)
    try:
        upload, shells = await anyio.to_thread.run_sync(lambda: service.add(data, filename))
    except UploadError as e:
        raise ApiError(e.status, e.message) from None
    return _describe(upload, shells)


@router.get(
    "/uploads/{upload_id}",
    description="Returns an upload with its shells as long as it has not expired",
    responses={403: ERROR_RESPONSE, 404: ERROR_RESPONSE},
)
def get_upload(
    settings: AppSettings,
    service: Uploads,
    upload_id: str = Path(pattern=UPLOAD_ID_PATTERN, description="id returned when uploading"),
):
    _check_enabled(settings)
    upload = service.get(upload_id)
    if upload is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "Upload nicht gefunden oder abgelaufen")
    return _describe(upload, service.shells(upload))


@router.delete(
    "/uploads/{upload_id}",
    status_code=HTTPStatus.NO_CONTENT,
    description="Deletes an upload and its shells before it expires",
    responses={403: ERROR_RESPONSE, 404: ERROR_RESPONSE},
)
def delete_upload(
    settings: AppSettings,
    service: Uploads,
    upload_id: str = Path(pattern=UPLOAD_ID_PATTERN, description="id returned when uploading"),
):
    _check_enabled(settings)
    if not service.remove(upload_id):
        raise ApiError(HTTPStatus.NOT_FOUND, "Upload nicht gefunden oder abgelaufen")
    return Response(status_code=HTTPStatus.NO_CONTENT)
