"""Antwortklassen."""

from __future__ import annotations

import json
from typing import Any

from fastapi.responses import JSONResponse, Response

# Inhalte, die ein Browser ausführen könnte. Sie werden nur als Download ausgeliefert (Schutz vor XSS über
# präparierte AASX-Dateien, die sonst im Origin der API laufen würden).
_ACTIVE_CONTENT = (
    "text/html",
    "application/xhtml",
    "image/svg",
    "text/xml",
    "application/xml",
    "javascript",
    "text/xsl",
    "application/x-shockwave-flash",
)


class AasJSONResponse(JSONResponse):
    """JSON kompakt in UTF-8, ``null`` für fehlende Werte."""

    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def file_response(data: bytes, content_type: str) -> Response:
    """Antwort für Attachments und Thumbnails aus AASX-Dateien."""
    response = Response(content=data, media_type=content_type)
    lowered = content_type.lower()
    if any(marker in lowered for marker in _ACTIVE_CONTENT):
        response.headers["Content-Disposition"] = "attachment"
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response
