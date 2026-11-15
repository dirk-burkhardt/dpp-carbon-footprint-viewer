"""ASGI-Middleware: Sicherheits-Header, CORS nur für die API, Schutz der Base64-IDs im Pfad."""

from __future__ import annotations

import urllib.parse
from collections.abc import Sequence
from typing import ClassVar, Optional

from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Setzt Header, die Browser vor Content-Sniffing, Framing und Referrer-Lecks schützen."""

    HEADERS: ClassVar[dict[str, str]] = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "SAMEORIGIN",
        "Cross-Origin-Resource-Policy": "cross-origin",
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class PrefixCORSMiddleware(CORSMiddleware):
    """CORS nur für Pfade unterhalb des API-Präfix (wie ``registry.addMapping(prefix + "/**")``)."""

    def __init__(
        self,
        app: ASGIApp,
        prefix: str,
        allow_origins: Sequence[str],
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = ("*",),
        allow_credentials: bool = False,
    ) -> None:
        super().__init__(
            app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
        )
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not scope["path"].startswith(self.prefix + "/"):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


class Base64SegmentMiddleware:
    """Schützt Base64-IDs im Pfad vor ``%2F``.

    Das Frontend codiert mit ``btoa``. Das erzeugt ``/``, das als ``%2F`` ankommt und nach dem Dekodieren den
    Pfad zerteilen würde. Für die ID-Segmente unter ``/shells/`` und ``/external-shells/`` wird daher aus dem
    Rohpfad das URL-sichere Alphabet erzeugt, bevor das Routing den Pfad sieht.
    """

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = prefix.strip("/").split("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and b"%2f" in scope.get("raw_path", b"").lower():
            new_path = self._rewrite(scope["raw_path"].decode("latin-1"))
            if new_path is not None:
                scope = dict(scope, path=new_path)
        await self.app(scope, receive, send)

    def _rewrite(self, raw_path: str) -> Optional[str]:
        segments = raw_path.split("/")
        n = len(self.prefix) + 1  # führender leerer Teil
        if segments[1:n] != self.prefix or len(segments) <= n + 1:
            return None
        if segments[n] == "external-shells":
            id_positions = [n + 1]
        elif segments[n] == "shells":
            id_positions = [n + 1]
            if len(segments) > n + 3 and segments[n + 2] == "submodels":
                id_positions.append(n + 3)
        else:
            return None
        decoded = [urllib.parse.unquote(s) for s in segments]
        for i in id_positions:
            decoded[i] = decoded[i].replace("/", "_").replace("+", "-")
        return "/".join(decoded)
