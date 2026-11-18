"""Erzeugt die FastAPI-Anwendung."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

import anyio
from fastapi import FastAPI

from . import API_PREFIX, __version__
from .api.errors import install_error_handlers
from .api.middleware import Base64SegmentMiddleware, PrefixCORSMiddleware, SecurityHeadersMiddleware
from .api.routes import build_api_router, health
from .api.static import install_static_files
from .config import Settings
from .repository import AssetRepository, InMemoryAssetRepository
from .services import ExternalShellService, HiddenShellLeases, UploadService

logger = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None, repository: Optional[AssetRepository] = None) -> FastAPI:
    """Erzeugt die Anwendung.

    Ohne ``repository`` wird ein In-Memory-Repository angelegt und beim Start (Lifespan) mit den Dateien aus
    ``settings`` gefüllt. Die API nimmt Anfragen erst an, wenn alle Dateien geladen sind.
    """
    settings = settings or Settings()
    load_files = repository is None
    repo: AssetRepository = repository or InMemoryAssetRepository(settings.max_entry_bytes)

    leases = HiddenShellLeases(repo)
    uploads = UploadService(
        repo,
        max_bytes=settings.upload_max_bytes,
        ttl_seconds=settings.upload_ttl_seconds,
        max_uploads=settings.upload_max_count,
        leases=leases,
        directory=settings.upload_dir,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if load_files and isinstance(repo, InMemoryAssetRepository):
            aas_files, aasx_files = settings.aas_files(), settings.aasx_files()
            await anyio.to_thread.run_sync(lambda: repo.load_files(aas_files, aasx_files))
            logger.info("%d Shells geladen", repo.shell_count())
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(_purge_periodically, app)
            yield
            tasks.cancel_scope.cancel()

    app = FastAPI(
        title="AAS(X) Carbon Footprint API",
        description="Backend for the generation of Carbon Footprints from AAS- and AASX-files.",
        version=__version__,
        docs_url="/api/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repo
    app.state.external_service = ExternalShellService(
        repo,
        max_bytes=settings.external_max_bytes,
        timeout_seconds=settings.external_timeout_seconds,
        max_cached=settings.external_max_cached,
        allow_private_networks=settings.external_allow_private_networks,
        leases=leases,
        ttl_seconds=settings.upload_ttl_seconds,
    )
    app.state.upload_service = uploads

    app.include_router(health.router)
    app.include_router(build_api_router())
    if settings.static_dir is not None:
        install_static_files(app, settings.static_dir)  # zuletzt, fängt alle übrigen GET-Pfade
    install_error_handlers(app, settings)

    # Middleware: die zuletzt hinzugefügte läuft zuerst
    if settings.cors_origins:
        logger.info("CORS für %s/** erlaubt von %s", API_PREFIX, ", ".join(settings.cors_origins))
        app.add_middleware(
            PrefixCORSMiddleware,
            prefix=API_PREFIX,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
            allow_credentials=False,  # die API nutzt keine Cookies oder Anmeldung
        )
    app.add_middleware(Base64SegmentMiddleware, prefix=API_PREFIX)
    app.add_middleware(SecurityHeadersMiddleware)
    return app


UPLOAD_PURGE_INTERVAL_SECONDS = 60.0


async def _purge_periodically(app: FastAPI) -> None:
    """Deletes expired uploads and downloads even if nobody accesses them (also done on every access)."""
    while True:
        await anyio.sleep(UPLOAD_PURGE_INTERVAL_SECONDS)
        await anyio.to_thread.run_sync(app.state.upload_service.purge_expired)
        await app.state.external_service.purge_expired()
