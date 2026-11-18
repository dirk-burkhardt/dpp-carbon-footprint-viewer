"""Temporary uploads of AAS/AASX files (``/uploads``).

Uploaded files are kept for a limited time only:

* the shells are added to the in-memory repository as hidden shells and never replace existing shells
* every upload gets a random, unguessable token; clients reference the upload (and share links) by this token
* an upload is removed after its time to live, when the number of uploads exceeds the limit (oldest first),
  on explicit deletion and, since nothing is written to disk, with every restart of the API
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import PurePosixPath
from typing import Optional

from ..aas import AasObject, AasParseError, AssetType
from ..repository import AssetRepository
from .leases import HiddenShellLeases

logger = logging.getLogger(__name__)

TOKEN_BYTES = 18  # 144 bit, URL-safe Base64 without padding (24 characters)
MAX_FILENAME_LENGTH = 200


class UploadError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Upload:
    """A stored upload; ``created`` and ``expires`` are Unix timestamps."""

    token: str
    filename: str
    size: int
    created: float
    expires: float
    shell_ids: list[str] = field(default_factory=list)


def asset_type_for(filename: str) -> AssetType:
    """Guesses the file format from the file name; unknown endings are detected from the content."""
    name = filename.lower()
    if name.endswith(".aasx"):
        return AssetType.AASX
    if name.endswith(".json"):
        return AssetType.JSON
    if name.endswith(".xml"):
        return AssetType.XML
    return AssetType.AUTO


def clean_filename(filename: Optional[str]) -> str:
    """Keeps only the last path segment and printable characters of a client supplied file name."""
    if not filename:
        return "upload"
    name = PurePosixPath(filename.replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:MAX_FILENAME_LENGTH] or "upload"


class UploadService:
    def __init__(
        self,
        repository: AssetRepository,
        *,
        max_bytes: int,
        ttl_seconds: float,
        max_uploads: int,
        leases: Optional[HiddenShellLeases] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._repository = repository
        self._leases = leases or HiddenShellLeases(repository)
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._max_uploads = max_uploads
        self._clock = clock
        self._uploads: OrderedDict[str, Upload] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, data: bytes, filename: Optional[str]) -> tuple[Upload, list[AasObject]]:
        """Parses ``data`` and stores its shells. Blocking, call it from a worker thread."""
        if len(data) > self.max_bytes:
            raise UploadError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Datei ist zu groß")
        if not data:
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Die Datei ist leer")
        name = clean_filename(filename)
        try:
            ids = self._repository.add_assets(data, asset_type_for(name), None, True, False)
        except AasParseError as e:
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, str(e)) from None
        if not ids:
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Die Datei enthält keine Asset Administration Shell")
        now = self._clock()
        upload = Upload(secrets.token_urlsafe(TOKEN_BYTES), name, len(data), now, now + self.ttl_seconds, ids)
        evicted: list[str] = []
        with self._lock:
            self._uploads[upload.token] = upload
            self._leases.acquire(self._owner(upload.token), ids)
            while len(self._uploads) > self._max_uploads:
                evicted.append(self._uploads.popitem(last=False)[0])
        for token in evicted:
            self._leases.release(self._owner(token))
        logger.info("Upload %s (%d Bytes) mit %d Shells gespeichert", name, len(data), len(ids))
        self.purge_expired()
        return upload, self.shells(upload)

    def get(self, token: str) -> Optional[Upload]:
        """The upload for ``token``, ``None`` if it is unknown or has expired."""
        self.purge_expired()
        with self._lock:
            return self._uploads.get(token)

    def remove(self, token: str) -> bool:
        with self._lock:
            upload = self._uploads.pop(token, None)
        if upload is None:
            return False
        self._leases.release(self._owner(token))
        return True

    def shells(self, upload: Upload) -> list[AasObject]:
        return [s for s in (self._repository.get_shell(i) for i in upload.shell_ids) if s is not None]

    def purge_expired(self) -> int:
        """Removes all expired uploads and returns their number."""
        now = self._clock()
        with self._lock:
            expired = [token for token, upload in self._uploads.items() if upload.expires <= now]
            for token in expired:
                del self._uploads[token]
        for token in expired:
            self._leases.release(self._owner(token))
        if expired:
            logger.info("%d abgelaufene Uploads entfernt", len(expired))
        return len(expired)

    def count(self) -> int:
        with self._lock:
            return len(self._uploads)

    @staticmethod
    def _owner(token: str) -> str:
        return f"upload:{token}"
