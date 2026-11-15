"""Lebenszyklusphasen nach EN 15804 (A1 … D) aus Freitext oder Listen lesen."""

from __future__ import annotations

import re
from collections.abc import Iterable
from itertools import pairwise

PHASES = (
    "A1", "A2", "A3", "A4", "A5",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7",
    "C1", "C2", "C3", "C4",
    "D",
)  # fmt: skip
_INDEX = {p: i for i, p in enumerate(PHASES)}
_PHASE = r"(?<![A-Za-z0-9])(?:[A-C]\d\d?|D)(?![A-Za-z0-9])"
# Phasen, Bereiche (A1-A3) und Listen (A1, A2; B1+B2) wie in der Oberfläche
_GROUP = re.compile(rf"{_PHASE}(?:[ \-–—―‒,;|+&/\\]+{_PHASE})*")


def parse_phases(values: str | Iterable[str] | None) -> list[str]:
    """Alle genannten Phasen, ohne Doppelte und in Reihenfolge des Lebenszyklus.

    ``"A1 - raw material supply"`` wird ``["A1"]``, ``"A1-A3"`` wird ``["A1", "A2", "A3"]``.
    """
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    found: set[str] = set()
    for value in values:
        for group in _GROUP.findall(value):
            normalized = re.sub(r"[–—―‒]", "-", group.replace(" ", ""))
            for part in re.split(r"[,;|+&/\\]", normalized):
                found.update(_range(part))
    return sorted(found, key=_INDEX.__getitem__)


def _range(part: str) -> list[str]:
    ends = [p for p in part.split("-") if p in _INDEX]
    if len(ends) < 2:
        return ends
    result: list[str] = []
    for a, b in pairwise(ends):
        lo, hi = sorted((_INDEX[a], _INDEX[b]))
        result.extend(PHASES[lo : hi + 1])
    return result
