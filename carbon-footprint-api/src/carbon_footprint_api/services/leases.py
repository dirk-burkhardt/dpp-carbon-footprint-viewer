"""Bookkeeping for hidden shells that are held on behalf of downloads and uploads.

Downloaded and uploaded files are added to the repository as hidden shells. Two sources may contain the same
shell (same ``id``), so a shell must only be removed from the repository once no source refers to it anymore.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable

from ..repository import AssetRepository


class HiddenShellLeases:
    """Reference counting of hidden shells per owner (a download URL or an upload token)."""

    def __init__(self, repository: AssetRepository) -> None:
        self._repository = repository
        self._owners: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def acquire(self, owner: str, shell_ids: Iterable[str]) -> None:
        """Registers ``shell_ids`` as used by ``owner`` (replaces an earlier registration of the same owner)."""
        with self._lock:
            self._owners[owner] = list(dict.fromkeys(shell_ids))

    def release(self, owner: str) -> None:
        """Forgets ``owner`` and removes its hidden shells that no other owner still uses."""
        with self._lock:
            released = self._owners.pop(owner, [])
            still_used = {shell_id for ids in self._owners.values() for shell_id in ids}
            orphaned = [shell_id for shell_id in released if shell_id not in still_used]
        if orphaned:
            # only_hidden: shells from the repository folder are never removed, even if a source contained them
            self._repository.remove_shells(orphaned, only_hidden=True)

    def owners(self) -> list[str]:
        with self._lock:
            return list(self._owners)
