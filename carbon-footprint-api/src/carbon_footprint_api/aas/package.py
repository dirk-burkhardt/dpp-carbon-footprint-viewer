"""Lesen von AASX-Paketen (OPC/ZIP) und Erkennung des Dateiformats."""

from __future__ import annotations

import io
import json
import logging
import posixpath
import zipfile
import zlib
from enum import Enum
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote

from lxml import etree

from .model import AasParseError, Environment, parse_json, parse_xml

logger = logging.getLogger(__name__)

# Obergrenze für die entpackte Größe eines einzelnen Eintrags (Schutz vor Zip-Bomben)
DEFAULT_MAX_ENTRY_BYTES = 256 * 1024 * 1024

# Beide Schreibweisen kommen in der Praxis vor (mit und ohne "www.")
_REL_ORIGIN = (
    "http://www.admin-shell.io/aasx/relationships/aasx-origin",
    "http://admin-shell.io/aasx/relationships/aasx-origin",
)
_REL_SPEC = (
    "http://www.admin-shell.io/aasx/relationships/aas-spec",
    "http://admin-shell.io/aasx/relationships/aas-spec",
)
_ZIP_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, OSError)


class AssetType(str, Enum):
    JSON = "JSON"
    XML = "XML"
    AASX = "AASX"
    AUTO = "AUTO"


class EntryTooLargeError(AasParseError):
    """Ein Eintrag im Paket überschreitet die erlaubte Größe."""


def _entry_name(target: str, base_part: str = "") -> str:
    """Löst ein Relationship-Ziel relativ zum Quell-Part auf und liefert den ZIP-Eintragsnamen."""
    target = unquote(target)
    path = target if target.startswith("/") else posixpath.join("/" + posixpath.dirname(base_part), target)
    return posixpath.normpath(path).lstrip("/")


def _rels_name(part: str) -> str:
    directory, name = posixpath.split(part)
    return posixpath.join(directory, "_rels", name + ".rels")


def _read_entry(zf: zipfile.ZipFile, name: str, max_bytes: int) -> Optional[bytes]:
    """Liest einen Eintrag. Bei doppelten Namen im ZIP gewinnt der letzte."""
    try:
        info = zf.getinfo(name)  # liefert bei doppelten Namen ebenfalls den letzten Eintrag
    except KeyError:
        return None
    if info.file_size > max_bytes:
        raise EntryTooLargeError(f"{name} ist entpackt {info.file_size} Bytes groß (erlaubt: {max_bytes})")
    return zf.read(info)


def _relationships(zf: zipfile.ZipFile, part: str, rel_types: tuple[str, ...], max_bytes: int) -> list[str]:
    data = _read_entry(zf, _rels_name(part), max_bytes)
    if data is None:
        return []
    try:
        root = etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError:
        return []
    return [
        _entry_name(rel.get("Target", ""), part)
        for rel in root
        if isinstance(rel.tag, str) and rel.get("Type") in rel_types and rel.get("Target")
    ]


def _find_spec_parts(zf: zipfile.ZipFile, max_bytes: int) -> list[str]:
    parts: list[str] = []
    for origin in _relationships(zf, "", _REL_ORIGIN, max_bytes):
        parts.extend(_relationships(zf, origin, _REL_SPEC, max_bytes))
    names = set(zf.namelist())
    missing = [p for p in parts if p not in names]
    if missing:
        logger.warning("AASX-Paket verweist auf fehlende Environments: %s", ", ".join(missing))
        parts = [p for p in parts if p in names]
    if not parts:
        # Fallback für Pakete mit fehlenden oder ungültigen Relationen (z. B. umbenannte .aas.xml). AASX 3.x
        # empfiehlt aasx/data.xml bzw. aasx/data.json, ältere Pakete nutzen *.aas.xml / *.aas.json.
        lowered = {n: n.lower() for n in zf.namelist()}
        parts = [n for n, low in lowered.items() if low.endswith((".aas.xml", ".aas.json"))]
        parts += [n for n, low in lowered.items() if low.rsplit("/", 1)[-1] in ("data.xml", "data.json")]
    # Dasselbe Environment kann in mehreren Formaten beiliegen (data.xml und data.json); XML hat Vorrang
    return sorted(dict.fromkeys(parts), key=lambda p: not p.lower().endswith(".xml"))


def read_aasx(data: bytes, max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES) -> Environment:
    """Liest das AAS-Environment aus einem AASX-Paket."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            parts = _find_spec_parts(zf, max_entry_bytes)
            if not parts:
                raise AasParseError("AASX-Paket enthält kein AAS-Environment")
            stems = {p.rsplit(".", 1)[0] for p in parts}
            if len(stems) > 1:
                logger.warning("AASX-Paket enthält mehrere Environments, verwende %s", parts[0])
            part = parts[0]
            content = _read_entry(zf, part, max_entry_bytes)
    except _ZIP_ERRORS as e:
        raise AasParseError(f"Kein gültiges oder ein beschädigtes AASX-Paket: {e}") from e
    if content is None:
        raise AasParseError(f"Environment {part} fehlt im AASX-Paket")
    if part.lower().endswith(".json"):
        return _parse_json_bytes(content)
    return parse_xml(content)


def _parse_json_bytes(data: bytes) -> Environment:
    try:
        loaded = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as e:
        raise AasParseError(f"Kein gültiges JSON: {e}") from e
    return parse_json(loaded)


def read_environment(
    data: bytes, asset_type: AssetType, max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES
) -> tuple[Environment, str]:
    """Liest ein Environment und liefert es mit der passenden Dateiendung (.json, .xml, .aasx).

    Bei ``AUTO`` wird nacheinander JSON, XML und AASX versucht. Ein zu großer Eintrag
    im AASX-Paket bricht sofort ab.
    """
    order = [asset_type] if asset_type != AssetType.AUTO else [AssetType.JSON, AssetType.XML, AssetType.AASX]
    last_error: Optional[Exception] = None
    for current in order:
        try:
            if current == AssetType.JSON:
                return _parse_json_bytes(data), ".json"
            if current == AssetType.XML:
                return parse_xml(data), ".xml"
            return read_aasx(data, max_entry_bytes), ".aasx"
        except EntryTooLargeError:
            raise
        except AasParseError as e:
            logger.debug("Konnte Daten nicht als %s lesen: %s", current.value, e)
            last_error = e
    raise AasParseError(f"Daten konnten nicht als AAS gelesen werden ({last_error})")


def read_attachment(
    package: Union[bytes, Path], path: Optional[str], max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES
) -> Optional[bytes]:
    """Liest eine Datei aus einem AASX-Paket. ``package`` ist der Dateipfad oder der Inhalt des Pakets."""
    if not path:
        return None
    try:
        source = io.BytesIO(package) if isinstance(package, bytes) else package
        with zipfile.ZipFile(source) as zf:
            name = path.lstrip("/")
            content = _read_entry(zf, name, max_entry_bytes)
            if content is None and unquote(name) != name:
                content = _read_entry(zf, unquote(name), max_entry_bytes)
    except EntryTooLargeError as e:
        logger.error("Attachment zu groß: %s", e)
        return None
    except _ZIP_ERRORS as e:
        logger.error("Fehler beim Lesen des AASX-Pakets: %s", e)
        return None
    if content is None:
        logger.warning("Datei %s nicht im AASX-Paket gefunden", path)
    return content
