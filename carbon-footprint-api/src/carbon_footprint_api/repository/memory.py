"""Hält die geladenen Shells und Submodels im Speicher."""

from __future__ import annotations

import base64
import binascii
import logging
import mimetypes
import re
import threading
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..aas import AasObject, AssetType, Environment, read_attachment, read_environment
from ..aas.package import DEFAULT_MAX_ENTRY_BYTES
from .base import Source

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchMatch:
    """Fundstelle der Volltextsuche: Submodel (idShort), idShortPath des Elements und gefundener Text."""

    submodel: Optional[str]
    path: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    """Shell mit ihren ersten Fundstellen und der Gesamtzahl der Fundstellen."""

    id: str
    global_asset_id: Optional[str]
    id_short: Optional[str]
    matches: list[SearchMatch]
    total: int


# Schlüssel, deren Inhalt die Volltextsuche nicht durchsucht (Metadaten, Verweise, Typangaben)
_SEARCH_SKIP_KEYS = frozenset(
    {
        "semanticId",
        "supplementalSemanticIds",
        "embeddedDataSpecifications",
        "qualifiers",
        "extensions",
        "administration",
        "contentType",
        "valueType",
        "valueTypeListElement",
        "typeValueListElement",
        "semanticIdListElement",
        "modelType",
        "kind",
        "category",
        "language",
        "type",
        "keys",
        "first",
        "second",
        "valueId",
        "submodels",
        "defaultThumbnail",
    }
)


def _search_texts(node: object, path: str) -> Iterable[tuple[str, str]]:
    """Liefert (idShortPath, Text) für alle durchsuchbaren Texte eines Elements und seiner Kinder."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, list):
        for index, child in enumerate(node):
            child_path = path
            if isinstance(child, dict) and child.get("idShort"):
                child_path = f"{path}.{child['idShort']}" if path else str(child["idShort"])
            elif isinstance(child, dict) and "language" not in child:
                child_path = f"{path}[{index}]"
            yield from _search_texts(child, child_path)
    elif isinstance(node, dict):
        is_blob = getattr(node, "model_type", None) == "Blob"
        for key, value in node.items():
            if key in _SEARCH_SKIP_KEYS or value is None or (is_blob and key == "value"):
                continue
            yield from _search_texts(value, path)


@dataclass(frozen=True, eq=False)
class _ShellEntry:
    shell: AasObject
    hidden: bool
    source: Optional[Source]


_INDEX = re.compile(r"(\[[0-9]+\])")
_IRDI_VERSION = re.compile(r"#\d{3}$")
# Anhang, mit dem der AASX Package Explorer doppelte IDs eindeutig macht (z. B. 0173-1#02-ABG855#001---4BAECD89)
_DUPLICATE_SUFFIX = re.compile(r"---[0-9A-Fa-f]{8}$")


def _strip_irdi_version(value: str) -> str:
    value = _DUPLICATE_SUFFIX.sub("", value.strip())
    return value if value.lower().startswith(("http://", "https://", "urn:")) else _IRDI_VERSION.sub("", value)


def split_id_short_path(path: str) -> list[str]:
    """Zerlegt einen idShortPath: ``a.b[2].c`` wird zu ``["a", "b", "[2]", "c"]``.

    Leere Teile (z. B. bei ``a..b``) bleiben erhalten, abschließende leere Teile entfallen wie bei ``String.split``.
    """
    names: list[str] = []
    for piece in path.split("."):
        if piece == "":
            names.append("")
            continue
        names.extend(part for part in _INDEX.split(piece) if part)
    while names and names[-1] == "":
        names.pop()
    return names


class InMemoryAssetRepository:
    """Stellt Shells, Submodels und Attachments aus AAS-, AASX- und JSON-Dateien bereit.

    Shells sind sowohl über ihre ``id`` als auch über ihre ``globalAssetId`` erreichbar. Es
    werden alle Submodels eines Environments jeder Shell dieses Environments zugeordnet.

    Schreibzugriffe und Lesezugriffe, die über alle Einträge laufen, sind über eine Sperre geschützt, denn
    heruntergeladene Dateien können zur Laufzeit hinzukommen und wieder entfernt werden.
    """

    def __init__(self, max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES) -> None:
        self._shells: dict[str, _ShellEntry] = {}
        self._submodels: dict[str, dict[str, AasObject]] = {}
        self._id_to_id_short: dict[str, Optional[str]] = {}
        # ConceptDescriptions aller Dateien des Repositorys (nicht aus heruntergeladenen); die erste gewinnt
        self._concept_descriptions: dict[str, AasObject] = {}
        self._cd_without_version: dict[str, AasObject] = {}  # IRDI ohne Versionsanhang (#001)
        self._lock = threading.RLock()
        self._max_entry_bytes = max_entry_bytes

    # ----------------------------------------------------------------------------------------------------------
    # Laden und Entfernen
    # ----------------------------------------------------------------------------------------------------------

    def load_files(self, aas_files: Iterable[Path] = (), aasx_files: Iterable[Path] = ()) -> None:
        """Lädt Dateien von der Kommandozeile. Fehler einzelner Dateien werden protokolliert und übersprungen."""
        for path, asset_type in [(p, AssetType.AUTO) for p in aas_files] + [(p, AssetType.AASX) for p in aasx_files]:
            logger.info("Lade %s", path.resolve())
            try:
                self.add_file(path, asset_type)
            except Exception:
                logger.exception("Fehler beim Laden von %s", path.resolve())

    def add_file(self, path: Path, asset_type: AssetType = AssetType.AUTO, hidden: bool = False) -> list[str]:
        return self.add_assets(path.read_bytes(), asset_type, source=path, hidden=hidden)

    def add_assets(
        self,
        data: bytes,
        asset_type: AssetType = AssetType.AUTO,
        source: Optional[Source] = None,
        hidden: bool = False,
        overwrite: bool = True,
    ) -> list[str]:
        """Liest ein Environment und fügt dessen Shells hinzu. Liefert die IDs der enthaltenen Shells.

        Ohne ``source`` dient der Inhalt selbst als Quelle für Attachments. Mit ``overwrite=False`` bleiben
        bereits registrierte Shells (gleiche ``id`` oder ``globalAssetId``) unverändert; ihre IDs werden
        trotzdem zurückgegeben.
        """
        env, _ = read_environment(data, asset_type, self._max_entry_bytes)
        self.add_environment(env, data if source is None else source, hidden, overwrite)
        return list(dict.fromkeys(s["id"] for s in env.shells))

    def add_environment(
        self, env: Environment, source: Optional[Source], hidden: bool = False, overwrite: bool = True
    ) -> None:
        with self._lock:
            shells = env.shells
            if not overwrite:
                existing = [s for s in shells if self._is_registered(s)]
                for shell in existing:
                    logger.warning("Shell %s ist bereits registriert und wird nicht ersetzt", shell["id"])
                shells = [s for s in shells if s not in existing]
            for shell in shells:
                self._add_shell(shell, source, hidden)
            for shell in shells:
                for submodel in env.submodels:
                    self._add_submodel_to_shell(shell, submodel)
            if not hidden:
                for cd in env.concept_descriptions:
                    if cd["id"]:
                        self._concept_descriptions.setdefault(cd["id"], cd)
                        self._cd_without_version.setdefault(_strip_irdi_version(cd["id"]), cd)

    def remove_shells(self, shell_ids: list[str], only_hidden: bool = True) -> None:
        """Entfernt Shells samt ihrer Submodel-Zuordnung (z. B. heruntergeladene Dateien aus dem Cache).

        Standardmäßig nur versteckte Shells, damit Dateien aus dem Repository nie entfernt werden.
        """
        with self._lock:
            for shell_id in shell_ids:
                entry = self._shells.get(shell_id)
                if entry is None or (only_hidden and not entry.hidden):
                    continue
                keys = {entry.shell["id"], entry.shell["assetInformation"]["globalAssetId"]}
                for key in keys:
                    if self._shells.get(key) is entry:
                        del self._shells[key]
                        self._submodels.pop(key, None)
                if self._shells.get(entry.shell["id"]) is None:
                    self._id_to_id_short.pop(entry.shell["id"], None)

    def _is_registered(self, shell: AasObject) -> bool:
        global_id = shell["assetInformation"]["globalAssetId"]
        return shell["id"] in self._shells or (global_id is not None and global_id in self._shells)

    def _add_shell(self, shell: AasObject, source: Optional[Source], hidden: bool) -> None:
        info = shell["assetInformation"]
        shell_id = shell["id"]
        global_id = info["globalAssetId"]
        if global_id is None:
            global_id = f"autogenerated_{shell_id}_{shell['idShort']}_{uuid.uuid4()}"
            info["globalAssetId"] = global_id
        self._id_to_id_short[shell_id] = shell["idShort"]
        logger.info("Füge Asset mit ID %s / globaler ID %s hinzu", shell_id, global_id)
        entry = _ShellEntry(shell, hidden, source)
        self._shells[global_id] = entry
        self._shells[shell_id] = entry

    def _add_submodel_to_shell(self, shell: AasObject, submodel: AasObject) -> None:
        shell_id = shell["id"]
        global_id = shell["assetInformation"]["globalAssetId"]
        self._add_submodel(shell_id, submodel)
        if shell_id != global_id:
            self._add_submodel(global_id, submodel)

    def _add_submodel(self, key: str, submodel: AasObject) -> None:
        submodels = self._submodels.setdefault(key, {})
        submodel_id = submodel["id"]
        if submodels.get(submodel_id) is submodel:
            # Mehrere Shells eines Environments mit derselben globalAssetId teilen sich die Submodels
            logger.debug("Submodel %s ist für Asset %s bereits registriert", submodel_id, key)
            return
        if submodel_id in submodels:
            if submodel["kind"] == "Template":
                logger.warning(
                    "Submodel-Template %s ist für Asset %s bereits registriert, wird übersprungen", submodel_id, key
                )
            else:
                logger.error("Submodel %s ist für Asset %s bereits registriert, wird übersprungen", submodel_id, key)
            return
        submodels[submodel_id] = submodel

    # ----------------------------------------------------------------------------------------------------------
    # Abfragen
    # ----------------------------------------------------------------------------------------------------------

    def shell_count(self) -> int:
        with self._lock:
            return len({id(e) for e in self._shells.values()})

    def has_shell(self, asset_id: str) -> bool:
        return asset_id in self._shells

    def get_shell(self, asset_id: str) -> Optional[AasObject]:
        entry = self._shells.get(asset_id)
        return None if entry is None else entry.shell

    def available_shell_ids(self) -> dict[str, Optional[str]]:
        """ID und idShort aller nicht versteckten Shells."""
        with self._lock:
            return {i: s for i, s in self._id_to_id_short.items() if i in self._shells and not self._shells[i].hidden}

    def shell_descriptors(self) -> list[AasObject]:
        with self._lock:
            entries = list({id(e): e for e in self._shells.values() if not e.hidden}.values())
        result = []
        for entry in entries:
            shell = entry.shell
            info = shell["assetInformation"]
            result.append(
                AasObject(
                    "AssetAdministrationShellDescriptor",
                    administration=shell["administration"],
                    assetKind=info["assetKind"],
                    assetType=info["assetType"],
                    endpoints=[],
                    globalAssetId=info["globalAssetId"],
                    id=shell["id"],
                    idShort=shell["idShort"],
                    specificAssetIds=info["specificAssetIds"],
                    submodelDescriptors=[],
                    description=shell["description"],
                    displayName=shell["displayName"],
                    extensions=[],
                )
            )
        return result

    def get_concept_description(self, cd_id: str) -> Optional[AasObject]:
        """ConceptDescription zur ID; IRDIs passen auch mit anderem Versionsanhang (``#002`` statt ``#001``)."""
        cd = self._concept_descriptions.get(cd_id)
        return cd if cd is not None else self._cd_without_version.get(_strip_irdi_version(cd_id))

    def concept_description_count(self) -> int:
        return len(self._concept_descriptions)

    def submodel_refs(self, asset_id: str) -> Optional[list]:
        shell = self.get_shell(asset_id)
        return None if shell is None else shell["submodels"]

    def has_submodel(self, asset_id: str, submodel_id: str) -> bool:
        return submodel_id in self._submodels.get(asset_id, {})

    def get_submodel(self, asset_id: str, submodel_id: str) -> Optional[AasObject]:
        return self._submodels.get(asset_id, {}).get(submodel_id)

    def available_submodel_ids(self, asset_id: str) -> Optional[list[str]]:
        """IDs der Submodels einer Shell, ``None`` wenn die Shell unbekannt ist."""
        with self._lock:
            submodels = self._submodels.get(asset_id)
            if submodels is None:
                return None if asset_id not in self._shells else []
            return list(submodels)

    def get_submodel_element(self, asset_id: str, submodel_id: str, id_short_path: str) -> Optional[AasObject]:
        """Sucht ein Element über seinen idShortPath (``a.b[0].c``).

        Es werden nur Collections (über idShort) und Listen (über Index) durchlaufen. Elemente ohne idShort
        werden bei der Namenssuche übersprungen.
        """
        submodel = self.get_submodel(asset_id, submodel_id)
        if submodel is None:
            return None
        names = split_id_short_path(id_short_path)
        if not names:
            return None
        element = _by_id_short(submodel["submodelElements"], names[0])
        for current in names[1:]:
            if element is None:
                return None
            if current == "":
                logger.debug("idShortPath %s enthält einen leeren Teil", id_short_path)
                return None
            if current.startswith("["):
                if element.model_type != "SubmodelElementList":
                    return None
                index = int(current[1:-1])
                values = element["value"]
                element = values[index] if index < len(values) else None
            elif element.model_type == "SubmodelElementCollection":
                element = _by_id_short(element["value"], current)
            else:
                return None
        return element

    def search(
        self, query: str, include_ids: Iterable[str] = (), max_matches: int = 3, limit: int = 200
    ) -> list[SearchHit]:
        """Volltextsuche (ohne Beachtung der Groß- und Kleinschreibung) in Shells und allen ihren Submodels.

        Durchsucht werden idShorts, Werte, mehrsprachige Texte und Beschreibungen, keine semantischen IDs oder
        Typangaben. Versteckte (heruntergeladene) Shells werden nur durchsucht, wenn ihre ID in ``include_ids``
        steht. Je Shell werden höchstens ``max_matches`` Fundstellen geliefert, insgesamt höchstens ``limit`` Shells.
        """
        needle = query.strip().casefold()
        if not needle:
            return []
        included = set(include_ids)
        with self._lock:
            entries = list({id(e): (key, e) for key, e in self._shells.items()}.values())
        hits: list[SearchHit] = []
        for _, entry in entries:
            shell = entry.shell
            global_id = shell["assetInformation"]["globalAssetId"]
            if entry.hidden and shell["id"] not in included and global_id not in included:
                continue
            matches: list[SearchMatch] = []
            total = 0
            sources: list[tuple[Optional[str], object]] = [(None, shell)]
            sources += [(sm["idShort"], sm) for sm in self._submodels.get(shell["id"], {}).values()]
            for submodel_name, source in sources:
                for path, text in _search_texts(source, ""):
                    if needle in text.casefold():
                        total += 1
                        if len(matches) < max_matches:
                            matches.append(SearchMatch(submodel_name, path, text))
            if total:
                hits.append(SearchHit(shell["id"], global_id, shell["idShort"], matches, total))
                if len(hits) >= limit:
                    break
        return hits

    def _get_attachment(self, asset_id: str, path: Optional[str]) -> Optional[bytes]:
        entry = self._shells.get(asset_id)
        if entry is None or entry.source is None:
            return None
        source = entry.source
        if isinstance(source, Path) and not source.is_file():
            logger.error("Quelldatei %s existiert nicht mehr", source)
            return None
        return read_attachment(source, path, self._max_entry_bytes)

    def get_submodel_element_attachment(
        self, asset_id: str, submodel_id: str, id_short_path: str
    ) -> Optional[tuple[bytes, str]]:
        """Inhalt und Content-Type eines File- oder Blob-Elements."""
        element = self.get_submodel_element(asset_id, submodel_id, id_short_path)
        if element is None:
            return None
        if element.model_type == "File":
            data = self._get_attachment(asset_id, element["value"])
            content_type, path = element["contentType"], element["value"]
        elif element.model_type == "Blob":
            try:
                data = None if element["value"] is None else base64.b64decode(element["value"])
            except (binascii.Error, ValueError):
                data = None
            content_type, path = element["contentType"], None
        else:
            return None
        if data is None:
            return None
        return data, content_type or guess_content_type(path)

    def get_thumbnail(self, asset_id: str) -> Optional[tuple[bytes, str]]:
        shell = self.get_shell(asset_id)
        if shell is None:
            return None
        thumbnail = shell["assetInformation"]["defaultThumbnail"]
        if thumbnail is None:
            return None
        data = self._get_attachment(asset_id, thumbnail["path"])
        if data is None:
            return None
        return data, thumbnail["contentType"] or guess_content_type(thumbnail["path"])


def _by_id_short(elements: list[AasObject], id_short: str) -> Optional[AasObject]:
    for element in elements:
        if element["idShort"] == id_short:
            return element
    return None


def guess_content_type(path: Optional[str]) -> str:
    """Content-Type aus dem Dateinamen, falls im Element keiner angegeben ist."""
    if path:
        guessed, _ = mimetypes.guess_type(path)
        if guessed:
            return guessed
    return "application/octet-stream"
