"""Bedeutung von Elementen aus ConceptDescriptions (Name, Einheit, Definition, Wertelisten)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from ..aas.model import AasObject
from .query import lang_text, normalize_semantic_id, semantic_id

ConceptLookup = Callable[[str], Optional[AasObject]]


class Semantics:
    """Liest die IEC-61360-Inhalte der ConceptDescription eines Elements oder seiner eingebetteten Spezifikation."""

    def __init__(self, lookup: Optional[ConceptLookup] = None) -> None:
        self._lookup = lookup

    def _contents(self, element: AasObject) -> list[AasObject]:
        result: list[AasObject] = []
        for source in [element, self._concept(element)]:
            if source is None:
                continue
            for eds in source.get("embeddedDataSpecifications") or []:
                content = eds.get("dataSpecificationContent")
                if content is not None:
                    result.append(content)
        return result

    def _concept(self, element: AasObject) -> Optional[AasObject]:
        sid = semantic_id(element)
        if not sid or self._lookup is None:
            return None
        return self._lookup(sid)

    def _first(self, element: AasObject, key: str) -> Optional[str]:
        for content in self._contents(element):
            value = content.get(key)
            if isinstance(value, list):
                value = lang_text(value)
            if value:
                return str(value).strip() or None
        return None

    def name(self, element: AasObject) -> Optional[str]:
        return lang_text(element.get("displayName")) or self._first(element, "preferredName")

    def unit(self, element: AasObject) -> Optional[str]:
        return self._first(element, "unit") or self._first(element, "symbol")

    def definition(self, element: AasObject) -> Optional[str]:
        return lang_text(element.get("description")) or self._first(element, "definition")

    def value_text(self, element: AasObject, value: Optional[str]) -> Optional[str]:
        """Text zu einem Wert-IRDI aus der Werteliste der ConceptDescription."""
        if not value:
            return value
        wanted = normalize_semantic_id(value)
        for content in self._contents(element):
            pairs = (content.get("valueList") or {}).get("valueReferencePairs") or []
            for pair in pairs:
                keys = ((pair.get("valueId") or {}).get("keys")) or []
                if keys and normalize_semantic_id(keys[0].get("value")) == wanted:
                    return pair.get("value") or value
        return value
