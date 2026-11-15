"""Versionsabhängige Parser für IDTA-Submodel-Templates und normalisierte Datenmodelle.

Die Parser lesen die Submodels im Antwortformat der API (:mod:`carbon_footprint_api.aas.model`) und liefern
versionsunabhängige Modelle (:mod:`.models`). Welche Templates und Versionen bekannt sind, steht in
``known_templates.json``; ``tools/check_idta_templates.py`` im Projekt vergleicht das mit GitHub.
"""

from .aggregation import summarize
from .carbon_footprint import parse_carbon_footprint
from .handover import parse_handover_documentation
from .hierarchy import Hierarchy, parse_hierarchy
from .maintenance import parse_maintenance_instructions
from .nameplate import parse_nameplate
from .registry import catalog, detect, families
from .semantics import Semantics
from .technical_data import parse_technical_data

__all__ = [
    "Hierarchy",
    "Semantics",
    "catalog",
    "detect",
    "families",
    "parse_carbon_footprint",
    "parse_handover_documentation",
    "parse_hierarchy",
    "parse_maintenance_instructions",
    "parse_nameplate",
    "parse_technical_data",
    "summarize",
]
