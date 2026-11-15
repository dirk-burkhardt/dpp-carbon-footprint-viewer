"""Parser für Maintenance Instructions (IDTA 02018) 1.0 bis 1.0.2."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Optional, TypeVar

from pydantic import BaseModel

from ..aas.model import AasObject
from .address import parse_address
from .models import (
    ItemUse,
    MaintenanceAlarm,
    MaintenanceInstructions,
    MaintenanceInterval,
    MaintenanceItem,
    MaintenanceStep,
    Quantity,
    TemplateInfo,
)
from .query import children, number, text
from .registry import detect
from .structure import entries, flag, named, one, reference_target, value


def _quantity(element: Optional[AasObject], value_names: list[str], unit_names: list[str]) -> Optional[Quantity]:
    if element is None:
        return None
    q = Quantity(value=number(one(element, value_names)), unit=value(element, unit_names))
    return q if q.value is not None or q.unit else None


def _uses(step: AasObject, kind: str) -> list[ItemUse]:
    """Werkzeuge/Verbrauchsmaterial/Ersatzteile eines Schritts (Referenz + Menge, auch mehrfach nummeriert)."""
    names = {
        "tools": ("ToolsForMaintenanceStep", "QuantityOfToolsForMaintenanceStep", None),
        "consumables": (
            "ConsumablesForMaintenanceStep",
            "QuantityOfConsumablesForMaintenanceStep",
            "UnitForQuantityOfConsumablesForMaintenanceStep",
        ),
        "spareParts": ("SparePartForMaintenanceStep", "QuantityOfSparePartForMaintenanceStep", None),
    }[kind]
    refs = named(step, [names[0]])
    quantities = named(step, [names[1]])
    units = named(step, [names[2]]) if names[2] else []
    result = []
    for i, ref in enumerate(refs):
        use = ItemUse(
            reference=reference_target(ref),
            quantity=number(quantities[i]) if i < len(quantities) else None,
            unit=text(units[i]) if i < len(units) else None,
        )
        if use.reference or use.quantity is not None:
            result.append(use)
    return result


def _step(item: AasObject) -> MaintenanceStep:
    return MaintenanceStep(
        id=value(item, ["MaintenanceStepID"]),
        name=value(item, ["MaintenanceStepName"]),
        localization=value(item, ["LocalizationDescription"]),
        instruction=value(item, ["InstructionMaintenanceStep"]),
        document=value(item, ["RelatedDocumentOrFileMaintenanceStep"]),
        tools=_uses(item, "tools"),
        consumables=_uses(item, "consumables"),
        spareParts=_uses(item, "spareParts"),
        duration=_quantity(
            one(item, ["EstimatedDurationTimeMaintenanceStep"]),
            ["ValueEstimatedDurationTimeMaintenanceStep"],
            ["UnitEstimatedDurationTimeMaintenanceStep"],
        ),
        signatureMandatory=flag(one(item, ["DocumentationSignatureMandatory"])),
        conditionForNextStep=value(item, ["ConditionForNextMaintenanceStep"]),
        nextStep=reference_target(one(item, ["NextMaintenanceStep"])),
        conditionForAlternativeNextStep=value(item, ["ConditionForAlternativeNextStep"]),
        alternativeNextStep=reference_target(one(item, ["AlternativeNextMaintenanceStep"])),
        endOfMaintenance=flag(one(item, ["EndOfMaintenance"])),
    )


def _interval(path: str, item: AasObject) -> MaintenanceInterval:
    basic = one(item, ["BasicMaintenanceInformation"])
    technicians = one(item, ["MaintenanceTechnicians"])
    contact = one(basic, ["ContactForMaintenanceAuthorization"])
    count = number(one(technicians, ["NumberOfRequiredTechnicians"]))
    alarms_holder = one(basic, ["AlarmValues"])
    return MaintenanceInterval(
        idShortPath=path,
        id=value(basic, ["MaintenanceID"]),
        name=value(basic, ["NameOfMaintenance"]),
        source=value(basic, ["SourceOfMaintenanceInstructions"]),
        interval=_quantity(
            one(basic, ["IntervalSpecification"]), ["MaintenanceIntervalValue"], ["MaintenanceIntervalUnit"]
        ),
        alarms=_filled(
            MaintenanceAlarm(
                name=value(a, ["AlarmName"]),
                warningLimitRelativeValue=number(one(a, ["WarningLimitRelativeValue"])),
                severity=value(a, ["WarningLimitSeverity"]),
            )
            for _, a in entries(alarms_holder, ["Alarms"], ["Alarm"])
        ),
        flowChart=value(basic, ["FlowChartOfMaintenanceSteps"]),
        relatedStandards=value(basic, ["RelatedStandardsLawsRegulations"]),
        safetyRegulations=value(basic, ["SafetyRegulationsToBeObserved"]),
        contact=parse_address(contact),
        contactCompany=value(contact, ["Company"]),
        technicians=int(count) if count is not None else None,
        requiredQualification=value(technicians, ["RequiredQualification"]),
        totalWorkingTime=_quantity(
            one(technicians, ["EstimatedTotalWorkingTime"]),
            ["ValueTotalEstimatedWorkingTime"],
            ["UnitValueTotalEstimatedWorkingTime"],
        ),
        steps=_filled(
            _step(s) for _, s in entries(one(item, ["ListMaintenanceSteps"]), ["MaintenanceSteps"], ["MaintenanceStep"])
        ),
    )


T = TypeVar("T", bound=BaseModel)


def _filled(models: Iterable[T]) -> list[T]:
    """Ohne Einträge, die nur aus leeren Template-Feldern bestehen."""
    return [m for m in models if any(v not in (None, [], "") for v in m.model_dump().values())]


def _items(submodel: AasObject, list_name: str, prefix: str) -> list[MaintenanceItem]:
    result = []
    for path, item in entries(submodel, [list_name], []):
        entry = MaintenanceItem(
            idShortPath=path,
            id=value(item, [f"{prefix}ID"]),
            name=value(item, [f"{prefix}Name"]),
            description=value(item, [f"{prefix}Description"]),
            supplier=value(item, [f"CompanyName{prefix}Supplier"]),
            orderCode=value(item, [f"OrderCode{prefix}OfManufacturer"]),
            link=value(item, [f"AddressOfAdditionalLink{prefix}"]),
        )
        if any(v for v in entry.model_dump(exclude={"idShortPath"}).values()):
            result.append(entry)
    return result


def parse_maintenance_instructions(
    submodel: AasObject, info: Optional[TemplateInfo] = None
) -> Optional[MaintenanceInstructions]:
    info = info or detect(submodel)
    if info.family != "maintenance-instructions":
        return None
    result = MaintenanceInstructions(templateVersion=info.version or info.variant, submodelId=submodel.get("id"))
    result.maintenanceFree = flag(one(submodel, ["MaintenanceFreeAsset"]))
    result.intervals = [
        _interval(path, item)
        for path, item in entries(submodel, [], ["MaintenanceInstructionsForSpecificInterval"])
        if children(item)
    ]
    result.tools = _items(submodel, "MaintenanceToolList", "Tool")
    result.consumables = _items(submodel, "MaintenanceConsumablesList", "Consumable")
    result.spareParts = _items(submodel, "MaintenanceSparePartList", "SparePart")
    return result
