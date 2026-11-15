"""Suche in Submodel-Elementen über SemanticId oder idShort (Gegenstück zu ``IdTree`` der Oberfläche).

IRDIs werden ohne Versionsanhang verglichen (``0173-1#02-ABG854#003`` passt auf ``…#001``), denn die
Templates erhöhen diese Versionen zwischen ihren Ausgaben, ohne die Bedeutung zu ändern.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from functools import cache
from importlib import resources
from typing import Optional

from ..aas.model import AasObject

_IRDI_VERSION = re.compile(r"#\d{3}$")
_DUPLICATE_SUFFIX = re.compile(r"---[0-9A-Fa-f]{8}$")  # vom AASX Package Explorer an doppelte IDs angehängt
PREFERRED_LANGUAGES = ("de", "en")


def normalize_semantic_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = _DUPLICATE_SUFFIX.sub("", value.strip())
    if "#" in value and not value.lower().startswith(("http://", "https://", "urn:")):
        value = _IRDI_VERSION.sub("", value)
    return value.rstrip("/")


def semantic_ids(element: AasObject) -> list[str]:
    """Werte der SemanticId und der zusätzlichen SemanticIds, normalisiert."""
    refs = [element.get("semanticId"), *(element.get("supplementalSemanticIds") or [])]
    result: list[str] = []
    for ref in refs:
        if not ref:
            continue
        for key in ref.get("keys") or []:
            norm = normalize_semantic_id(key.get("value"))
            if norm:
                result.append(norm)
    return result


def semantic_id(element: AasObject) -> Optional[str]:
    """Erster Wert der SemanticId im Original (für Ausgaben und Versionserkennung)."""
    ref = element.get("semanticId")
    keys = (ref or {}).get("keys") or []
    return keys[0].get("value") if keys else None


def children(element: AasObject) -> list[AasObject]:
    t = element.model_type
    if t in ("SubmodelElementCollection", "SubmodelElementList"):
        return list(element.get("value") or [])
    if t == "Entity":
        return list(element.get("statements") or [])
    if t == "Submodel":
        return list(element.get("submodelElements") or [])
    if t == "AnnotatedRelationshipElement":
        return list(element.get("annotations") or [])
    return []


def matches(element: AasObject, sids: Iterable[str] = (), id_shorts: Iterable[str] = ()) -> bool:
    wanted = {normalize_semantic_id(s) for s in sids}
    if wanted & set(semantic_ids(element)):
        return True
    id_short = element.get("idShort")
    return id_short is not None and id_short.lower() in {i.lower() for i in id_shorts}


def find_all(
    element: AasObject, sids: Iterable[str] = (), id_shorts: Iterable[str] = (), deep: bool = False
) -> Iterator[AasObject]:
    """Kinder (bei ``deep`` alle Nachfahren), die über SemanticId oder idShort passen.

    Wie in der Oberfläche haben SemanticId-Treffer Vorrang: passt ein Kind über die SemanticId, werden
    Kinder, die nur über den idShort passen, nicht geliefert.
    """
    sids = list(sids)
    id_shorts = list(id_shorts)
    by_sid: list[AasObject] = []
    by_short: list[AasObject] = []
    for child in _descendants(element) if deep else children(element):
        if sids and matches(child, sids=sids):
            by_sid.append(child)
        elif id_shorts and matches(child, id_shorts=id_shorts):
            by_short.append(child)
    yield from by_sid or by_short


def find(element: Optional[AasObject], sids: Iterable[str] = (), id_shorts: Iterable[str] = ()) -> Optional[AasObject]:
    """Erstes passendes Kind oder ``None``."""
    if element is None:
        return None
    return next(find_all(element, sids, id_shorts), None)


def _descendants(element: AasObject) -> Iterator[AasObject]:
    for child in children(element):
        yield child
        yield from _descendants(child)


# --------------------------------------------------------------------------------------------------------------
# Werte
# --------------------------------------------------------------------------------------------------------------


def lang_text(values: Optional[list], languages: Iterable[str] = PREFERRED_LANGUAGES) -> Optional[str]:
    """Text einer Liste von LangStrings in bevorzugter Sprache (sonst der erste nicht leere)."""
    if not values:
        return None
    texts = [(str(v.get("language") or "").lower(), v.get("text")) for v in values if v.get("text")]
    for lang in languages:
        for code, text in texts:
            if code == lang or code.startswith(lang + "-"):
                return str(text).strip()
    return str(texts[0][1]).strip() if texts else None


@cache
def _value_ids() -> dict[str, str]:
    raw = resources.files(__package__).joinpath("value_ids.json").read_text(encoding="utf-8")
    values: dict[str, str] = json.loads(raw)["values"]
    return values


def resolve_value_id(value: Optional[str]) -> Optional[str]:
    """Text zu einem ECLASS-Wert-IRDI (``0173-1#07-ABU221#002`` wird ``GHG Protocol``), sonst ``None``."""
    if not value or "#07-" not in value:
        return None
    return _value_ids().get(_IRDI_VERSION.sub("", value.strip()))


def text(element: Optional[AasObject]) -> Optional[str]:
    """Wert von Property, MultiLanguageProperty oder File als Text (leer wird ``None``).

    Wert-IRDIs aus Wertelisten (im Wert oder in ``valueId``) werden in ihren Text übersetzt.
    """
    if element is None:
        return None
    value = element.get("value")
    if element.model_type == "MultiLanguageProperty":
        return lang_text(value)
    if not isinstance(value, str) or not value.strip():
        value_id = element.get("valueId")
        keys = (value_id or {}).get("keys") or []
        return resolve_value_id(keys[0].get("value")) if keys else None
    value = value.strip()
    return resolve_value_id(value) or value


def number(element: Optional[AasObject]) -> Optional[float]:
    value = text(element)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def texts(element: Optional[AasObject]) -> list[str]:
    """Werte einer Liste (SubmodelElementList) oder eines einzelnen Elements."""
    if element is None:
        return []
    if element.model_type in ("SubmodelElementList", "SubmodelElementCollection"):
        return [t for t in (text(c) for c in children(element)) if t]
    value = text(element)
    return [value] if value else []
