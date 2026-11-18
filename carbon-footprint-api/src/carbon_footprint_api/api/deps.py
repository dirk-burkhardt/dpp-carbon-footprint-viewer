"""Abhängigkeiten für die Routen (FastAPI Depends)."""

from __future__ import annotations

import base64
import binascii
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Request

from ..config import Settings
from ..repository import AssetRepository
from ..services import ExternalShellService, UploadService
from .errors import ApiError


def get_repository(request: Request) -> AssetRepository:
    return request.app.state.repository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_external_service(request: Request) -> ExternalShellService:
    return request.app.state.external_service


def get_upload_service(request: Request) -> UploadService:
    return request.app.state.upload_service


Repository = Annotated[AssetRepository, Depends(get_repository)]
External = Annotated[ExternalShellService, Depends(get_external_service)]
Uploads = Annotated[UploadService, Depends(get_upload_service)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def decode_id(value: str, name: str) -> str:
    """Dekodiert eine Base64-codierte ID (mit oder ohne Padding).

    Akzeptiert das URL-sichere Alphabet (Spezifikation) und das Standardalphabet, denn das Frontend
    codiert mit ``btoa``.
    """
    try:
        value = value.replace("+", "-").replace("/", "_")
        padded = value + "=" * (-len(value) % 4)
        return base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8", errors="replace")
    except (binascii.Error, ValueError):
        raise ApiError(HTTPStatus.BAD_REQUEST, f"{name} ist nicht UTF8-BASE64-URL-codiert") from None
