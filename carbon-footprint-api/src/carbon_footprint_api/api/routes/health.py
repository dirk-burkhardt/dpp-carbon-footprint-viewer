"""Statusendpunkt für Container-Healthchecks."""

from __future__ import annotations

from fastapi import APIRouter

from ... import __version__
from ..deps import Repository

router = APIRouter(tags=["Health"])


@router.get("/api/health", description="Liveness and readiness of the API")
def health(repo: Repository):
    return {"status": "ok", "version": __version__, "shells": repo.shell_count()}
