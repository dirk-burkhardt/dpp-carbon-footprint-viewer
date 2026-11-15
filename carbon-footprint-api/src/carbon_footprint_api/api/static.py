"""Auslieferung statischer Dateien (z. B. gebautes Frontend) mit SPA-Fallback."""

from __future__ import annotations

import mimetypes
from http import HTTPStatus
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Unter Windows liest mimetypes die Registry, dort ist .js teils als text/plain eingetragen.
# Browser laden ES-Module dann nicht, daher werden die Typen für Web-Dateien fest gesetzt.
for _type, _ext in (
    ("text/javascript", ".js"),
    ("text/javascript", ".mjs"),
    ("text/css", ".css"),
    ("application/json", ".json"),
    ("image/svg+xml", ".svg"),
    ("application/wasm", ".wasm"),
    ("text/html", ".html"),
    ("image/png", ".png"),
    ("image/x-icon", ".ico"),
    ("application/manifest+json", ".webmanifest"),
):
    mimetypes.add_type(_type, _ext)


def static_file(base: Path, relative: str) -> Optional[Path]:
    """Datei unterhalb von ``base`` oder ``None``; verhindert Zugriffe außerhalb des Ordners."""
    base = base.resolve()
    try:
        target = (base / relative.lstrip("/")).resolve()
    except (OSError, ValueError):
        return None
    if target != base and base not in target.parents:
        return None
    return target if target.is_file() else None


def install_static_files(app: FastAPI, static_dir: Path) -> None:
    @app.api_route("/{resource:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def static_resource(resource: str):
        target = static_file(static_dir, resource or "index.html")
        if target is None:
            raise StarletteHTTPException(HTTPStatus.NOT_FOUND)
        return FileResponse(target)
