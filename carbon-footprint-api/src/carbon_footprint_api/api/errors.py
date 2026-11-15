"""Fehlerobjekte und Fehlerbehandlung."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..config import Settings
from .responses import AasJSONResponse
from .static import static_file

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Fehler, der als JSON-Fehlerobjekt beantwortet wird."""

    def __init__(self, status: int, message: Optional[str] = None) -> None:
        super().__init__(message)
        self.status = int(status)
        self.message = message


ERROR_RESPONSE: dict[str, Any] = {
    "description": "Fehlerobjekt mit timestamp, status, error, message und path",
    "content": {
        "application/json": {
            "example": {
                "timestamp": "2026-01-01T00:00:00.000Z",
                "status": 404,
                "error": "Not Found",
                "message": "Asset Administration Shell not found",
                "path": "/api/v4/shells/...",
            }
        }
    },
}


def _plain_error(status: int) -> PlainTextResponse:
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = "Error"
    return PlainTextResponse(f"Error {status} - {phrase}", status_code=status)


def install_error_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        status = HTTPStatus(exc.status)
        return AasJSONResponse(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "status": status.value,
                "error": status.phrase,
                "message": exc.message,
                "path": request.url.path,
            },
            status_code=status.value,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == HTTPStatus.NOT_FOUND and settings.not_found_resource and settings.static_dir:
            target = static_file(settings.static_dir, settings.not_found_resource)
            if target is not None:
                status = HTTPStatus.OK if settings.suppress_404 else HTTPStatus.NOT_FOUND
                return FileResponse(target, status_code=status)
        response = _plain_error(exc.status_code)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return _plain_error(HTTPStatus.BAD_REQUEST)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unerwarteter Fehler bei %s", request.url.path)
        return _plain_error(HTTPStatus.INTERNAL_SERVER_ERROR)
