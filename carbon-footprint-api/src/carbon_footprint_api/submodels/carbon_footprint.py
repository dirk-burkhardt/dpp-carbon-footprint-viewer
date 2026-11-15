"""Parser für Carbon-Footprint-Submodels aller bekannten Versionen.

* 0.9 (IDTA 02023-0-9): je eine Collection ProductCarbonFootprint/TransportCarbonFootprint, mehrere Submodels
  CarbonFootprint{00}, {01}, … je Shell möglich
* 1.0-Entwurf: Struktur wie 0.9, aber SemanticIds …/1/0 (ältere Beispieldateien)
* 1.0 bis 1.0.3 (IDTA 02023-1-0-x, Metamodell 3.0 und 3.1): Listen ProductCarbonFootprints und
  ProductOrSectorSpecificCarbonFootprints, kein TransportCarbonFootprint mehr
* Digital Battery Passport Teil 3 (IDTA 02035-3): Profil von 1.0 mit PerformanceClass und Studien-Links
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from ..aas.model import AasObject
from .address import parse_address
from .lifecycle import parse_phases
from .models import ExternalPcfApi, Footprint, FootprintKind, SectorRule, TemplateInfo
from .query import children, find, find_all, matches, number, semantic_ids, text, texts
from .registry import detect

CF = "https://admin-shell.io/idta/CarbonFootprint/"
PCF_COLLECTION = (CF + "ProductCarbonFootprint/0/9", CF + "ProductCarbonFootprint/1/0")
TCF_COLLECTION = (CF + "TransportCarbonFootprint/0/9", CF + "TransportCarbonFootprint/1/0")
PCF_LIST = CF + "ProductCarbonFootprints/1/0"
SECTOR_LIST = CF + "ProductOrSectorSpecificCarbonFootprints/1/0"
SECTOR_ITEM = CF + "ProductOrSectorSpecificCarbonFootprint/1/0"
PUBLICATION_DATE = (CF + "PublicationDate/1/0",)
EXPIRATION_DATE = (CF + "ExpirationDate/1/0", CF + "ExpirationnDate/1/0")  # Schreibfehler im Template 0.9
EXPLANATORY_STATEMENT = (CF + "ExplanatoryStatement/1/0",)
ADDRESS_INFORMATION = "https://admin-shell.io/zvei/nameplate/1/0/ContactInformations/AddressInformation"
BATTERY = "urn:samm:io.admin-shell.idta.batterypass.carbon_footprint:1.0.0#"

Spec = tuple[tuple[str, ...], tuple[str, ...]]

# Gemeinsame Felder von PCF (P) und TCF (T): (SemanticIds, idShorts)
P_METHOD: Spec = (
    ("0173-1#02-ABG854", CF + "PcfCalculationMethods/1/0"),
    ("PcfCalculationMethods", "PCFCalculationMethod"),
)
P_CO2EQ: Spec = (("0173-1#02-ABG855",), ("PcfCO2eq", "PCFCO2eq"))
P_UNIT: Spec = (("0173-1#02-ABG856",), ("ReferenceImpactUnitForCalculation", "PCFReferenceValueForCalculation"))
P_QUANTITY: Spec = (("0173-1#02-ABG857",), ("QuantityOfMeasureForCalculation", "PCFQuantityOfMeasureForCalculation"))
P_PHASES: Spec = (
    ("0173-1#02-ABG858", CF + "LifeCyclePhases/1/0"),
    ("LifeCyclePhases", "PCFLifeCyclePhase", "PCFLiveCyclePhase"),
)
P_HANDOVER: Spec = (("0173-1#02-ABI497", ADDRESS_INFORMATION), ("GoodsHandoverAddress", "PCFGoodsAddressHandover"))
T_METHOD: Spec = (("0173-1#02-ABG859",), ("TCFCalculationMethod",))
T_CO2EQ: Spec = (("0173-1#02-ABG860",), ("TCFCO2eq",))
T_UNIT: Spec = (("0173-1#02-ABG861",), ("TCFReferenceValueForCalculation",))
T_QUANTITY: Spec = (("0173-1#02-ABG862",), ("TCFQuantityOfMeasureForCalculation",))
T_PROCESS: Spec = (("0173-1#02-ABG863",), ("TCFProcessesForGreenhouseGasEmissionInATransportService",))
T_TAKEOVER: Spec = (("0173-1#02-ABI499",), ("TCFGoodsTransportAddressTakeover",))
T_HANDOVER: Spec = (("0173-1#02-ABI498",), ("TCFGoodsTransportAddressHandover",))


def _get(element: AasObject, spec: Spec) -> Optional[AasObject]:
    return find(element, *spec)


def _common(fp: Footprint, item: AasObject) -> None:
    fp.publicationDate = text(find(item, PUBLICATION_DATE, ("PublicationDate",)))
    fp.expirationDate = text(find(item, EXPIRATION_DATE, ("ExpirationDate",)))
    fp.explanatoryStatement = text(find(item, EXPLANATORY_STATEMENT, ("ExplanatoryStatement",)))


def _values(fp: Footprint, item: AasObject, method: Spec, co2eq: Spec, unit: Spec, quantity: Spec) -> None:
    fp.calculationMethods = texts(_get(item, method))
    fp.co2eq = number(_get(item, co2eq))
    if fp.co2eq is None:
        fp.warnings.append("Kein gültiger CO2eq-Wert angegeben")
    fp.referenceUnit = text(_get(item, unit))
    fp.quantity = number(_get(item, quantity))


def _product(item: AasObject, version: str, submodel_id: Optional[str], path: str) -> Footprint:
    fp = Footprint(kind="product", templateVersion=version, submodelId=submodel_id, idShortPath=path)
    _values(fp, item, P_METHOD, P_CO2EQ, P_UNIT, P_QUANTITY)
    fp.lifeCyclePhasesText = texts(_get(item, P_PHASES))
    fp.lifeCyclePhases = parse_phases(fp.lifeCyclePhasesText)
    if fp.lifeCyclePhasesText and not fp.lifeCyclePhases:
        fp.warnings.append(f"Lebenszyklusphase nicht erkannt: {', '.join(fp.lifeCyclePhasesText)}")
    fp.goodsHandoverAddress = parse_address(_get(item, P_HANDOVER))
    fp.performanceClass = text(find(item, (BATTERY + "performanceClass",), ("PerformanceClass",)))
    fp.publicStudyLinks = texts(
        find(item, (BATTERY + "webLinkToPublicCarbonFootprintStudy",), ("WebLinkToPublicCarbonFootprintStudy",))
    )
    _common(fp, item)
    return fp


def _transport_process(value: Optional[str], fp: Footprint) -> None:
    if not value:
        fp.transportProcess = "WTW"
        fp.warnings.append(
            "Nicht angegeben, ob Well-to-Tank, Tank-to-Wheel oder beides berechnet wurde; behandelt als Well-to-Wheel"
        )
        return
    for code in ("WTT", "TTW", "WTW"):
        if value.upper().startswith(code):
            fp.transportProcess = code  # type: ignore[assignment]
            return
    fp.warnings.append(f"Unbekannter Transportprozess: {value}")


def _transport(item: AasObject, version: str, submodel_id: Optional[str], path: str) -> Footprint:
    fp = Footprint(kind="transport", templateVersion=version, submodelId=submodel_id, idShortPath=path)
    _values(fp, item, T_METHOD, T_CO2EQ, T_UNIT, T_QUANTITY)
    # Transport wird als Phase A4 dargestellt (gezählt wird jede Strecke, siehe aggregation)
    fp.lifeCyclePhases = ["A4"]
    _transport_process(text(_get(item, T_PROCESS)), fp)
    fp.goodsTakeoverAddress = parse_address(_get(item, T_TAKEOVER))
    fp.goodsHandoverAddress = parse_address(_get(item, T_HANDOVER))
    _common(fp, item)
    return fp


def _sector_specific(item: AasObject, submodel_id: Optional[str], path: str) -> Footprint:
    kind: FootprintKind = "productOrSectorSpecific"
    fp = Footprint(kind=kind, templateVersion="1.0", submodelId=submodel_id, idShortPath=path)
    fp.calculationMethods = texts(_get(item, P_METHOD))
    rule = find(item, (CF + "ProductOrSectorSpecificRule/1/0",), ("ProductOrSectorSpecificRule",))
    if rule is not None:
        fp.rule = SectorRule(
            operator=text(find(rule, (), ("PcfRuleOperator",))),
            name=text(find(rule, (), ("PcfRuleName",))),
            version=text(find(rule, (), ("PcfRuleVersion",))),
            onlineReference=text(find(rule, (), ("PcfRuleOnlineReference",))),
        )
    api = find(item, (CF + "ExternalPcfApi/1/0",), ("ExternalPcfApi",))
    if api is not None:
        fp.externalApi = ExternalPcfApi(
            endpoint=text(find(api, (CF + "ExternalPcfApi/Endpoint/1/0",), ("PcfApiEndpoint",))),
            query=text(find(api, (CF + "ExternalPcfApi/Query/1/0",), ("PcfApiQuery",))),
        )
    info = find(item, (CF + "PcfInformation/1/0",), ("PcfInformation",))
    fp.information = [t for t in (text(c) for c in children(info)) if t] if info is not None else []
    return fp


def _items(lst: AasObject) -> Iterable[tuple[str, AasObject]]:
    name = lst.get("idShort") or ""
    for i, item in enumerate(children(lst)):
        yield f"{name}[{i}]", item


def parse_carbon_footprint(submodel: AasObject, info: Optional[TemplateInfo] = None) -> list[Footprint]:
    """Alle Einträge eines Carbon-Footprint-Submodels, leere Liste bei fremden Submodels."""
    info = info or detect(submodel)
    if info.family != "carbon-footprint" or info.isTemplate:
        return []
    sm_id = submodel.get("id")
    result: list[Footprint] = []
    if info.version == "1.0" and info.variant != "1.0-Entwurf":
        for lst in find_all(submodel, (PCF_LIST,), ("ProductCarbonFootprints",)):
            result.extend(_product(item, "1.0", sm_id, path) for path, item in _items(lst))
        for lst in find_all(submodel, (SECTOR_LIST,), ("ProductOrSectorSpecificCarbonFootprints",)):
            result.extend(_sector_specific(item, sm_id, path) for path, item in _items(lst))
        return result
    version = "0.9" if info.version == "0.9" else "1.0-Entwurf"
    for item in _collections(submodel, PCF_COLLECTION, "ProductCarbonFootprint"):
        result.append(_product(item, version, sm_id, item.get("idShort") or ""))
    for item in _collections(submodel, TCF_COLLECTION, "TransportCarbonFootprint"):
        result.append(_transport(item, version, sm_id, item.get("idShort") or ""))
    return result


def _collections(submodel: AasObject, sids: tuple[str, ...], prefix: str) -> list[AasObject]:
    """Collections über SemanticId oder, ohne SemanticId, über den idShort-Anfang (z. B. ProductCarbonFootprint_2)."""
    result = []
    for child in children(submodel):
        if child.model_type != "SubmodelElementCollection":
            continue
        if matches(child, sids=sids) or (not semantic_ids(child) and (child.get("idShort") or "").startswith(prefix)):
            result.append(child)
    return result
