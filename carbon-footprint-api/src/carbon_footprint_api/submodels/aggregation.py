"""Zusammenfassung mehrerer Footprint-Einträge eines Produkts.

Regeln:

* Produkt-Footprints werden nur innerhalb derselben Berechnungsmethode addiert, nie über Methoden hinweg
  (sonst würde dieselbe Emission doppelt gezählt).
* Innerhalb einer Methode zählt jede Lebenszyklusphase höchstens einmal. Überlappen sich Einträge (z. B. A1-A3
  und einzeln A1, A2, A3), werden die feiner aufgeteilten gezählt und die übrigen als übersprungen markiert.
* Einträge ohne erkannte Phase werden immer gezählt (wie bisher in der Oberfläche).
* Hauptmethode ist die erste vorhandene aus ``PREFERRED_METHODS``, sonst die zuerst genannte.
* Transport-Footprints (nur 0.9 und 1.0-Entwurf) sind einzelne Strecken und werden alle addiert.
"""

from __future__ import annotations

from typing import Optional

from .lifecycle import PHASES
from .models import Footprint, FootprintSummary, MethodTotal

PREFERRED_METHODS = ("ISO 14067", "GHG Protocol", "EN 15804", "ISO 14040", "ISO 14044")


def method_key(fp: Footprint) -> str:
    methods = sorted({m.strip() for value in fp.calculationMethods for m in value.split(",") if m.strip()})
    return ", ".join(methods) or "ohne Angabe"


def _method_total(method: str, entries: list[tuple[int, Footprint]]) -> MethodTotal:
    covered: set[str] = set()
    counted: list[int] = []
    skipped: list[int] = []
    for index, fp in sorted(entries, key=lambda e: (len(e[1].lifeCyclePhases) or len(PHASES) + 1, e[0])):
        phases = set(fp.lifeCyclePhases)
        if phases and phases & covered:
            skipped.append(index)
            continue
        covered |= phases
        counted.append(index)
    lookup = dict(entries)
    co2 = sum(lookup[i].co2eq or 0.0 for i in counted)
    return MethodTotal(
        method=method,
        co2eq=co2,
        coveredPhases=[p for p in PHASES if p in covered],
        countedEntries=sorted(counted),
        skippedEntries=sorted(skipped),
    )


def _primary(methods: list[str]) -> Optional[str]:
    for preferred in PREFERRED_METHODS:
        for method in methods:
            if preferred in method.split(", "):
                return method
    return methods[0] if methods else None


def summarize(footprints: list[Footprint]) -> FootprintSummary:
    groups: dict[str, list[tuple[int, Footprint]]] = {}
    transport = 0.0
    for i, fp in enumerate(footprints):
        if fp.co2eq is None:
            continue
        if fp.kind == "product":
            groups.setdefault(method_key(fp), []).append((i, fp))
        elif fp.kind == "transport":
            transport += fp.co2eq
    totals = [_method_total(m, e) for m, e in groups.items()]
    primary = _primary([t.method for t in totals])
    summary = FootprintSummary(primaryMethod=primary, transportCo2eq=transport, methods=totals)
    main = next((t for t in totals if t.method == primary), None)
    if main is not None:
        summary.productCo2eq = main.co2eq
        summary.coveredPhases = list(main.coveredPhases)
        if main.skippedEntries:
            summary.warnings.append(
                f"{len(main.skippedEntries)} Eintrag/Einträge mit überlappenden Lebenszyklusphasen nicht gezählt"
            )
    if len(totals) > 1:
        summary.warnings.append(
            f"Footprints nach {len(totals)} Methoden vorhanden; gezählt wird nur {primary}, "
            "die übrigen sind Alternativen"
        )
    if transport and "A4" in summary.coveredPhases:
        summary.warnings.append("Transport (A4) ist zusätzlich im Produkt-Footprint enthalten und wird zweimal gezählt")
    if transport and "A4" not in summary.coveredPhases:
        summary.coveredPhases = [p for p in PHASES if p in {*summary.coveredPhases, "A4"}]
    summary.totalCo2eq = summary.productCo2eq + summary.transportCo2eq
    return summary
