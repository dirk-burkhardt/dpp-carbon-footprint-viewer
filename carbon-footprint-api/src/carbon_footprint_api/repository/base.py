"""Schnittstelle der Datenhaltung.

Die API greift nur über diese Schnittstelle auf Daten zu. Eine spätere Implementierung, z. B. mit einer
Datenbank, kann die In-Memory-Variante ersetzen, ohne die Routen zu ändern.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, Union, runtime_checkable

from ..aas import AasObject, AssetType

# Quelle einer Shell: Pfad der Datei oder bei heruntergeladenen Dateien deren Inhalt
Source = Union[Path, bytes]


@runtime_checkable
class AssetRepository(Protocol):
    def shell_count(self) -> int: ...

    def has_shell(self, asset_id: str) -> bool: ...

    def get_shell(self, asset_id: str) -> Optional[AasObject]: ...

    def available_shell_ids(self) -> dict[str, Optional[str]]: ...

    def shell_descriptors(self) -> list[AasObject]: ...

    def submodel_refs(self, asset_id: str) -> Optional[list]: ...

    def has_submodel(self, asset_id: str, submodel_id: str) -> bool: ...

    def get_submodel(self, asset_id: str, submodel_id: str) -> Optional[AasObject]: ...

    def available_submodel_ids(self, asset_id: str) -> Optional[list[str]]: ...

    def get_submodel_element(self, asset_id: str, submodel_id: str, id_short_path: str) -> Optional[AasObject]: ...

    def get_submodel_element_attachment(
        self, asset_id: str, submodel_id: str, id_short_path: str
    ) -> Optional[tuple[bytes, str]]: ...

    def get_thumbnail(self, asset_id: str) -> Optional[tuple[bytes, str]]: ...

    def add_assets(
        self,
        data: bytes,
        asset_type: AssetType = AssetType.AUTO,
        source: Optional[Source] = None,
        hidden: bool = False,
        overwrite: bool = True,
    ) -> list[str]: ...

    def remove_shells(self, shell_ids: list[str], only_hidden: bool = True) -> None: ...
