"""Routen der API."""

from fastapi import APIRouter

from ... import API_PREFIX
from ..responses import AasJSONResponse
from . import assets, external, health, shells


def build_api_router() -> APIRouter:
    router = APIRouter(prefix=API_PREFIX, default_response_class=AasJSONResponse)
    router.include_router(external.router)
    router.include_router(shells.router)
    router.include_router(assets.router)
    return router


__all__ = ["build_api_router", "health"]
