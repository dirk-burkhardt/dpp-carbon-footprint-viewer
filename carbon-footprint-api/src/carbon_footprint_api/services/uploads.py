"""Temporary uploads of AAS/AASX files (``/uploads``).

Uploaded files are kept for a limited time only:

* the shells are added to the in-memory repository as hidden shells and never replace existing shells
* every upload gets a random, unguessable token; clients reference the upload (and share links) by this token
* an upload is removed after its time to live, when the number of uploads exceeds the limit (oldest first),
  on explicit deletion and with every restart of the API
* with an upload directory (``CFA_UPLOAD_DIR``, in the container ``repo/uploads``) the files are stored there,
  separated from the static repository, and attachments are read from the file instead of memory. Only files
  named by this service (``<upload id>.<ending>``) are ever deleted; all of them are removed on startup. Without
  a directory, or if it is not writable, uploads are kept in memory only.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import tempfile
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path, PurePosixPath
from typing import Optional

from ..aas import AasObject, AasParseError, AssetType
from ..repository import AssetRepository
from .leases import HiddenShellLeases

logger = logging.getLogger(__name__)

TOKEN_BYTES = 18  # 144 bit, URL-safe Base64 without padding (24 characters)
MAX_FILENAME_LENGTH = 200
STORED_ENDINGS = (".aasx", ".json", ".xml", ".bin")
# Files written by this service; nothing else in the upload directory is touched
STORED_FILE = re.compile(r"^[A-Za-z0-9_-]{24}\.(aasx|json|xml|bin)$")


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
    path: Optional[Path] = None


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
        directory: Optional[Path] = None,
    ) -> None:
        self._repository = repository
        self._leases = leases or HiddenShellLeases(repository)
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._max_uploads = max_uploads
        self._clock = clock
        self._uploads: OrderedDict[str, Upload] = OrderedDict()
        # Files of removed uploads whose shells another upload or download still uses
        self._pending_files: list[tuple[Path, list[str]]] = []
        self._lock = threading.Lock()
        self.directory = self._prepare_directory(directory)

    @staticmethod
    def _prepare_directory(directory: Optional[Path]) -> Optional[Path]:
        """Creates the directory and removes files of earlier runs. None if uploads stay in memory."""
        if directory is None:
            return None
        try:
            directory.mkdir(parents=True, exist_ok=True)
            removed = 0
            for path in directory.iterdir():
                if path.is_file() and STORED_FILE.match(path.name):
                    path.unlink()
                    removed += 1
            # Check that files can be written
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".write-test-"):
                pass
        except OSError as e:
            logger.warning("Upload-Verzeichnis %s nicht nutzbar (%s), Uploads nur im Arbeitsspeicher", directory, e)
            return None
        if removed:
            logger.info("%d Uploads früherer Läufe aus %s gelöscht", removed, directory)
        logger.info("Uploads werden in %s abgelegt", directory)
        return directory

    def add(self, data: bytes, filename: Optional[str]) -> tuple[Upload, list[AasObject]]:
        """Parses ``data`` and stores its shells. Blocking, call it from a worker thread."""
        if len(data) > self.max_bytes:
            raise UploadError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Datei ist zu groß")
        if not data:
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Die Datei ist leer")
        name = clean_filename(filename)
        token = secrets.token_urlsafe(TOKEN_BYTES)
        path = self._store(token, name, data)
        try:
            ids = self._repository.add_assets(data, asset_type_for(name), path, True, False)
        except AasParseError as e:
            self._delete_file(path)
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, str(e)) from None
        if not ids:
            self._delete_file(path)
            raise UploadError(HTTPStatus.UNPROCESSABLE_ENTITY, "Die Datei enthält keine Asset Administration Shell")
        now = self._clock()
        upload = Upload(token, name, len(data), now, now + self.ttl_seconds, ids, path)
        evicted: list[Upload] = []
        with self._lock:
            self._uploads[upload.token] = upload
            self._leases.acquire(self._owner(upload.token), ids)
            while len(self._uploads) > self._max_uploads:
                evicted.append(self._uploads.popitem(last=False)[1])
        for old in evicted:
            self._release(old)
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
        self._release(upload)
        return True

    def shells(self, upload: Upload) -> list[AasObject]:
        return [s for s in (self._repository.get_shell(i) for i in upload.shell_ids) if s is not None]

    def purge_expired(self) -> int:
        """Removes all expired uploads and returns their number."""
        now = self._clock()
        with self._lock:
            expired = [upload for upload in self._uploads.values() if upload.expires <= now]
            for upload in expired:
                del self._uploads[upload.token]
        for upload in expired:
            self._release(upload)
        self._delete_pending_files()
        if expired:
            logger.info("%d abgelaufene Uploads entfernt", len(expired))
        return len(expired)

    def count(self) -> int:
        with self._lock:
            return len(self._uploads)

    @staticmethod
    def _owner(token: str) -> str:
        return f"upload:{token}"

    def _store(self, token: str, filename: str, data: bytes) -> Optional[Path]:
        """Writes the upload to the upload directory (atomically). None if uploads stay in memory."""
        if self.directory is None:
            return None
        ending = next((e for e in STORED_ENDINGS if filename.lower().endswith(e)), ".bin")
        path = self.directory / f"{token}{ending}"
        try:
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix=".upload-", delete=False) as tmp:
                tmp.write(data)
            os.replace(tmp.name, path)
        except OSError as e:
            logger.error("Upload konnte nicht gespeichert werden: %s", e)
            raise UploadError(HTTPStatus.INSUFFICIENT_STORAGE, "Upload konnte nicht gespeichert werden") from None
        return path

    def _release(self, upload: Upload) -> None:
        """Releases the shells of an upload and deletes its file once no other source uses its shells.

        Shells are never replaced: if another upload or download contains the same shell, the repository keeps the
        entry of the file that was loaded first, whose attachments are read from that file.
        """
        self._leases.release(self._owner(upload.token))
        if upload.path is None:
            return
        with self._lock:
            self._pending_files.append((upload.path, upload.shell_ids))
        self._delete_pending_files()

    def _delete_pending_files(self) -> None:
        with self._lock:
            pending, self._pending_files = self._pending_files, []
            for path, ids in pending:
                if self._leases.in_use(ids) and any(self._repository.has_shell(i) for i in ids):
                    self._pending_files.append((path, ids))
                else:
                    self._delete_file(path)

    @staticmethod
    def _delete_file(path: Optional[Path]) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("Upload %s konnte nicht gelöscht werden: %s", path, e)
