"""Robuste Suche über idShorts für Templates, deren SemanticIds sich zwischen Versionen stark ändern.

Wiederholte Elemente heißen je nach Version ``Document01``, ``Document__00__``, ``Document{00}`` oder stehen ohne
idShort in einer SubmodelElementList (``Documents``). :func:`base_name` entfernt die Zähler.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Optional

from ..aas.model import AasObject
from .query import children, matches, text

_COUNTER = re.compile(r"(?:__\d+__|\{\d+\}|_\d+|\d+)$")


def base_name(id_short: Optional[str]) -> str:
    return _COUNTER.sub("", id_short or "").lower()


def named(element: Optional[AasObject], names: Iterable[str], sids: Iterable[str] = ()) -> list[AasObject]:
    """Kinder, deren idShort ohne Zähler einem der Namen entspricht oder deren SemanticId passt."""
    if element is None:
        return []
    wanted = {n.lower() for n in names}
    sids = list(sids)
    return [c for c in children(element) if base_name(c.get("idShort")) in wanted or (sids and matches(c, sids=sids))]


def one(element: Optional[AasObject], names: Iterable[str], sids: Iterable[str] = ()) -> Optional[AasObject]:
    found = named(element, names, sids)
    return found[0] if found else None


def value(element: Optional[AasObject], names: Iterable[str], sids: Iterable[str] = ()) -> Optional[str]:
    return text(one(element, names, sids))


def entries(
    element: Optional[AasObject],
    list_names: Iterable[str],
    item_names: Iterable[str],
    item_sids: Iterable[str] = (),
) -> Iterator[tuple[str, AasObject]]:
    """Wiederholte Einträge: Kinder einer Liste (``Documents``) und einzelne Collections (``Document01``, oder mit
    beliebigem idShort, aber passender SemanticId).

    Liefert (idShortPath relativ zum Element, Eintrag).
    """
    lists = {n.lower() for n in list_names}
    items = {n.lower() for n in item_names}
    sids = list(item_sids)
    for child in children(element) if element is not None else []:
        name = base_name(child.get("idShort"))
        if child.model_type == "SubmodelElementList" and (child.get("idShort") or "").lower() in lists:
            for i, item in enumerate(children(child)):
                yield f"{child.get('idShort')}[{i}]", item
        elif child.model_type != "SubmodelElementList" and (name in items or (sids and matches(child, sids=sids))):
            yield child.get("idShort") or "", child


def flag(element: Optional[AasObject]) -> Optional[bool]:
    v = text(element)
    if v is None:
        return None
    return v.strip().lower() in ("true", "1", "yes", "ja")


def reference_target(element: Optional[AasObject]) -> Optional[str]:
    """Letzter Schlüssel einer ReferenceElement-Referenz (z. B. idShort eines Werkzeugs)."""
    if element is None or element.model_type != "ReferenceElement":
        return None
    keys = (element.get("value") or {}).get("keys") or []
    return keys[-1].get("value") if keys else None
