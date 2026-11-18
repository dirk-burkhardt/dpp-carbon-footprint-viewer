"""Laden von Shells aus einer URL (``/external-shells``).

Schutzmaßnahmen, weil hier der Server im Auftrag eines Clients beliebige Adressen abruft:

* nur http und https
* kein Zugriff auf localhost, private, link-lokale oder reservierte Netze (SSRF), geprüft vor der Verbindung
  über DNS und nach dem Verbindungsaufbau über die tatsächliche Gegenstelle (gegen DNS-Rebinding),
  bei jeder Weiterleitung erneut
* Größen- und Zeitlimit, Proxy-Variablen der Umgebung werden ignoriert
* heruntergeladene Shells sind versteckt, ersetzen nie vorhandene Shells und werden nach dem LRU-Prinzip
  wieder entfernt, damit der Speicher nicht unbegrenzt wächst
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Optional

import anyio
import httpx2

from .. import __version__
from ..aas import AasObject, AasParseError, AssetType
from ..repository import AssetRepository
from .leases import HiddenShellLeases

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 5
Resolver = Callable[[str, int], Awaitable[list[str]]]


class ExternalDownloadError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


async def _resolve(host: str, port: int) -> list[str]:
    infos = await anyio.to_thread.run_sync(lambda: socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class ExternalShellService:
    def __init__(
        self,
        repository: AssetRepository,
        *,
        max_bytes: int,
        timeout_seconds: float,
        max_cached: int,
        allow_private_networks: bool = False,
        transport: Optional[httpx2.AsyncBaseTransport] = None,
        resolver: Resolver = _resolve,
        leases: Optional[HiddenShellLeases] = None,
    ) -> None:
        self._repository = repository
        # Shared with the upload service, so a shell contained in a download and an upload stays while one uses it
        self._leases = leases or HiddenShellLeases(repository)
        self._max_bytes = max_bytes
        self._timeout = timeout_seconds
        self._max_cached = max_cached
        self._allow_private = allow_private_networks
        self._transport = transport
        self._resolver = resolver
        self._cache: OrderedDict[str, list[str]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def load(self, url: str) -> Optional[list[AasObject]]:
        """Shells aus der Datei unter ``url``. ``None`` bedeutet: die Gegenstelle lieferte nicht 200."""
        async with self._lock:
            cached = self._cache.get(url)
            if cached is not None:
                self._cache.move_to_end(url)
        if cached is None:
            data = await self._download(url)
            if data is None:
                return None
            try:
                ids = await anyio.to_thread.run_sync(
                    lambda: self._repository.add_assets(data, AssetType.AUTO, None, True, False)
                )
            except AasParseError as e:
                raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, str(e)) from None
            if not ids:
                raise ExternalDownloadError(HTTPStatus.NOT_FOUND, "Die Datei enthält keine Asset Administration Shell")
            await self._remember(url, ids)
            cached = ids
        return [s for s in (self._repository.get_shell(i) for i in cached) if s is not None]

    async def _remember(self, url: str, ids: list[str]) -> None:
        async with self._lock:
            self._cache[url] = ids
            self._cache.move_to_end(url)
            self._leases.acquire(f"url:{url}", ids)
            while len(self._cache) > self._max_cached:
                evicted_url, _ = self._cache.popitem(last=False)
                self._leases.release(f"url:{evicted_url}")

    async def _check_url(self, url: httpx2.URL) -> None:
        if url.scheme not in ("http", "https") or not url.host:
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Nur http- und https-URLs werden unterstützt")
        if self._allow_private:
            return
        port = url.port or (443 if url.scheme == "https" else 80)
        try:
            addresses = await self._resolver(url.host, port)
        except OSError as e:
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, f"Host nicht auflösbar: {e}") from None
        if not addresses or not all(is_public_address(a) for a in addresses):
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Zieladresse ist nicht öffentlich erreichbar")

    def _check_peer(self, response: httpx2.Response) -> None:
        if self._allow_private:
            return
        stream = response.extensions.get("network_stream")
        peer = stream.get_extra_info("server_addr") if stream is not None else None
        if peer and not is_public_address(str(peer[0])):
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Zieladresse ist nicht öffentlich erreichbar")

    async def _download(self, raw_url: str) -> Optional[bytes]:
        try:
            url = httpx2.URL(raw_url)
        except (httpx2.InvalidURL, ValueError, TypeError) as e:
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, f"Ungültige URL: {e}") from None
        headers = {"User-Agent": f"carbon-footprint-api/{__version__}"}
        try:
            with anyio.fail_after(self._timeout):
                async with httpx2.AsyncClient(
                    transport=self._transport,
                    timeout=self._timeout,
                    follow_redirects=False,
                    trust_env=False,
                    headers=headers,
                ) as client:
                    for _ in range(MAX_REDIRECTS + 1):
                        await self._check_url(url)
                        async with client.stream("GET", url) as response:
                            self._check_peer(response)
                            if response.is_redirect and "location" in response.headers:
                                url = url.join(response.headers["location"])
                                continue
                            if response.status_code != 200:
                                logger.info("Download von %s lieferte %s", raw_url, response.status_code)
                                return None
                            return await self._read_limited(response)
                    raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Zu viele Weiterleitungen")
        except TimeoutError:
            raise ExternalDownloadError(HTTPStatus.GATEWAY_TIMEOUT, "Zeitüberschreitung beim Download") from None
        except httpx2.TimeoutException:
            raise ExternalDownloadError(HTTPStatus.GATEWAY_TIMEOUT, "Zeitüberschreitung beim Download") from None
        except httpx2.HTTPError as e:
            message = f"Download fehlgeschlagen: {type(e).__name__}"
            raise ExternalDownloadError(HTTPStatus.BAD_GATEWAY, message) from None

    async def _read_limited(self, response: httpx2.Response) -> bytes:
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self._max_bytes:
            raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Datei ist zu groß")
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self._max_bytes:
                raise ExternalDownloadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Datei ist zu groß")
            chunks.append(chunk)
        return b"".join(chunks)
