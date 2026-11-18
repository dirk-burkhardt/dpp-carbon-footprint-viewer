"""Normalisierte, versionsunabhängige Datenmodelle der fachlichen Endpunkte."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TemplateInfo(BaseModel):
    """Erkanntes IDTA-Template eines Submodels."""

    submodelId: Optional[str]
    idShort: Optional[str]
    semanticId: Optional[str]
    family: Optional[str] = Field(description="Schlüssel der Template-Familie, z. B. carbon-footprint")
    name: Optional[str] = None
    idta: Optional[str] = None
    version: Optional[str] = Field(default=None, description="Version laut SemanticId und Struktur, z. B. 1.0")
    variant: Optional[str] = Field(default=None, description="z. B. 1.0-Entwurf oder Battery-Passport-Profil")
    parsing: Literal["full", "detect", "none"] = "none"
    isTemplate: bool = Field(default=False, description="Leere Template-Kopie ohne verwertbare Werte")


class Address(BaseModel):
    street: Optional[str] = None
    houseNumber: Optional[str] = None
    zipcode: Optional[str] = None
    cityTown: Optional[str] = None
    stateCounty: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def is_empty(self) -> bool:
        return all(v is None for v in self.model_dump().values())


class SectorRule(BaseModel):
    operator: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    onlineReference: Optional[str] = None


class ExternalPcfApi(BaseModel):
    endpoint: Optional[str] = None
    query: Optional[str] = None


FootprintKind = Literal["product", "transport", "productOrSectorSpecific"]


class Footprint(BaseModel):
    """Ein Carbon-Footprint-Eintrag (PCF oder TCF), unabhängig von der Template-Version."""

    kind: FootprintKind
    templateVersion: str = Field(description="0.9, 1.0-Entwurf oder 1.0")
    submodelId: Optional[str] = None
    idShortPath: Optional[str] = None
    calculationMethods: list[str] = []
    co2eq: Optional[float] = Field(default=None, description="kg CO2-Äquivalent")
    referenceUnit: Optional[str] = Field(default=None, description="Bezugseinheit, z. B. piece oder kg")
    quantity: Optional[float] = Field(default=None, description="Menge der Bezugseinheit")
    lifeCyclePhases: list[str] = Field(default=[], description="Normalisierte Phasen A1 … D")
    lifeCyclePhasesText: list[str] = Field(default=[], description="Phasen wie in der Datei angegeben")
    transportProcess: Optional[Literal["WTT", "TTW", "WTW"]] = None
    goodsHandoverAddress: Optional[Address] = None
    goodsTakeoverAddress: Optional[Address] = None
    publicationDate: Optional[str] = None
    expirationDate: Optional[str] = None
    explanatoryStatement: Optional[str] = None
    performanceClass: Optional[str] = None
    publicStudyLinks: list[str] = []
    rule: Optional[SectorRule] = None
    externalApi: Optional[ExternalPcfApi] = None
    information: list[str] = []
    warnings: list[str] = []


class MethodTotal(BaseModel):
    method: str = Field(description="Berechnungsmethode(n), durch Komma getrennt")
    co2eq: float
    coveredPhases: list[str]
    countedEntries: list[int] = Field(description="Indizes der gezählten Einträge in footprints")
    skippedEntries: list[int] = Field(description="Wegen überlappender Phasen nicht gezählte Einträge")


class FootprintSummary(BaseModel):
    """Zusammenfassung: je Methode über die Phasen summiert, nie über Methoden hinweg."""

    primaryMethod: Optional[str] = None
    productCo2eq: float = 0.0
    transportCo2eq: float = 0.0
    totalCo2eq: float = 0.0
    coveredPhases: list[str] = []
    methods: list[MethodTotal] = []
    warnings: list[str] = []


class CarbonFootprintResult(BaseModel):
    footprints: list[Footprint] = []
    summary: FootprintSummary = FootprintSummary()
    templates: list[TemplateInfo] = []


class Nameplate(BaseModel):
    templateVersion: Optional[str] = None
    submodelId: Optional[str] = None
    manufacturerName: Optional[str] = None
    productDesignation: Optional[str] = None
    productFamily: Optional[str] = None
    serialNumber: Optional[str] = None
    yearOfConstruction: Optional[str] = None
    countryOfOrigin: Optional[str] = None
    address: Optional[Address] = None


class LangText(BaseModel):
    language: Optional[str] = None
    text: Optional[str] = None


class ProductNode(BaseModel):
    """Knoten des Produktbaums über alle Shells (aus Hierarchical Structures)."""

    globalAssetId: str
    shellId: Optional[str] = Field(default=None, description="None, wenn keine Shell zur globalAssetId existiert")
    idShort: Optional[str] = None
    displayName: list[LangText] = []
    description: list[LangText] = []
    entityIdShort: Optional[str] = None
    relationIdShort: Optional[str] = None
    bulkCount: Optional[float] = None
    nameplate: Optional[Nameplate] = None
    carbonFootprint: Optional[CarbonFootprintResult] = None
    children: list[ProductNode] = []
    warnings: list[str] = []


class ProductTree(BaseModel):
    root: ProductNode
    archeType: Optional[str] = None
    hierarchyVersion: Optional[str] = None
    nodeCount: int = 0
    warnings: list[str] = []


# --------------------------------------------------------------------------------------------------------------
# Technical Data (IDTA 02003)
# --------------------------------------------------------------------------------------------------------------


class FileRef(BaseModel):
    path: Optional[str] = None
    contentType: Optional[str] = None


class Classification(BaseModel):
    system: Optional[str] = None
    version: Optional[str] = None
    url: Optional[str] = None
    classId: Optional[str] = None
    className: Optional[str] = None


class TechnicalProperty(BaseModel):
    """Ein Merkmal; Name, Einheit und Definition kommen auch aus den ConceptDescriptions der Datei."""

    path: list[str] = Field(default=[], description="Abschnitte (Collections/Listen) oberhalb des Merkmals")
    idShort: Optional[str] = None
    name: Optional[str] = None
    semanticId: Optional[str] = None
    modelType: str
    valueType: Optional[str] = None
    value: Optional[str] = None
    min: Optional[str] = None
    max: Optional[str] = None
    unit: Optional[str] = None
    definition: Optional[str] = None


class PropertyArea(BaseModel):
    name: Optional[str] = None
    properties: list[TechnicalProperty] = []


class TechnicalData(BaseModel):
    templateVersion: Optional[str] = None
    submodelId: Optional[str] = None
    manufacturerName: Optional[str] = None
    productDesignation: Optional[str] = None
    articleNumber: Optional[str] = None
    orderCode: Optional[str] = None
    logo: Optional[FileRef] = None
    productImages: list[FileRef] = []
    classifications: list[Classification] = []
    areas: list[PropertyArea] = []
    specificDescriptions: list[PropertyArea] = []
    textStatement: Optional[str] = None
    validDate: Optional[str] = None


# --------------------------------------------------------------------------------------------------------------
# Handover Documentation (IDTA 02004, VDI 2770)
# --------------------------------------------------------------------------------------------------------------


class DocumentId(BaseModel):
    domainId: Optional[str] = None
    id: Optional[str] = None
    isPrimary: Optional[bool] = None


class DocumentVersion(BaseModel):
    languages: list[str] = []
    version: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    statusSetDate: Optional[str] = None
    statusValue: Optional[str] = None
    role: Optional[str] = None
    organizationName: Optional[str] = None
    organizationOfficialName: Optional[str] = None
    digitalFiles: list[FileRef] = []
    previewFile: Optional[FileRef] = None


class Document(BaseModel):
    idShortPath: Optional[str] = None
    ids: list[DocumentId] = []
    classifications: list[Classification] = []
    versions: list[DocumentVersion] = []


class HandoverDocumentation(BaseModel):
    templateVersion: Optional[str] = None
    submodelId: Optional[str] = None
    documents: list[Document] = []


# --------------------------------------------------------------------------------------------------------------
# Maintenance Instructions (IDTA 02018)
# --------------------------------------------------------------------------------------------------------------


class Quantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None


class MaintenanceAlarm(BaseModel):
    name: Optional[str] = None
    warningLimitRelativeValue: Optional[float] = None
    severity: Optional[str] = None


class ItemUse(BaseModel):
    """Verweis eines Wartungsschritts auf Werkzeug, Verbrauchsmaterial oder Ersatzteil."""

    reference: Optional[str] = Field(default=None, description="Ziel der Referenz (letzter Schlüssel)")
    quantity: Optional[float] = None
    unit: Optional[str] = None


class MaintenanceStep(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    localization: Optional[str] = None
    instruction: Optional[str] = None
    document: Optional[str] = None
    tools: list[ItemUse] = []
    consumables: list[ItemUse] = []
    spareParts: list[ItemUse] = []
    duration: Optional[Quantity] = None
    signatureMandatory: Optional[bool] = None
    conditionForNextStep: Optional[str] = None
    nextStep: Optional[str] = None
    conditionForAlternativeNextStep: Optional[str] = None
    alternativeNextStep: Optional[str] = None
    endOfMaintenance: Optional[bool] = None


class MaintenanceInterval(BaseModel):
    idShortPath: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    source: Optional[str] = None
    interval: Optional[Quantity] = None
    alarms: list[MaintenanceAlarm] = []
    flowChart: Optional[str] = None
    relatedStandards: Optional[str] = None
    safetyRegulations: Optional[str] = None
    contact: Optional[Address] = None
    contactCompany: Optional[str] = None
    technicians: Optional[int] = None
    requiredQualification: Optional[str] = None
    totalWorkingTime: Optional[Quantity] = None
    steps: list[MaintenanceStep] = []


class MaintenanceItem(BaseModel):
    """Werkzeug, Verbrauchsmaterial oder Ersatzteil aus den Listen des Submodels."""

    idShortPath: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    orderCode: Optional[str] = None
    link: Optional[str] = None


class MaintenanceInstructions(BaseModel):
    templateVersion: Optional[str] = None
    submodelId: Optional[str] = None
    maintenanceFree: Optional[bool] = None
    intervals: list[MaintenanceInterval] = []
    tools: list[MaintenanceItem] = []
    consumables: list[MaintenanceItem] = []
    spareParts: list[MaintenanceItem] = []


class ProductDetails(BaseModel):
    """Alle ausgewerteten Submodels einer Shell."""

    templates: list[TemplateInfo] = []
    nameplate: Optional[Nameplate] = None
    technicalData: list[TechnicalData] = []
    documentation: list[HandoverDocumentation] = []
    maintenance: list[MaintenanceInstructions] = []


# --------------------------------------------------------------------------------------------------------------
# Reference quantities for carbon footprint intensities (derived from Technical Data)
# --------------------------------------------------------------------------------------------------------------


class MeasureSource(BaseModel):
    """Where a reference quantity was found."""

    submodelId: Optional[str] = None
    path: list[str] = []
    idShort: Optional[str] = None
    name: Optional[str] = None
    semanticId: Optional[str] = None
    value: Optional[str] = Field(default=None, description="Value as given in the file")
    unit: Optional[str] = Field(default=None, description="Unit as given in the file (or in the value)")


class Measure(BaseModel):
    value: float = Field(description="Value in the SI unit of the measure")
    unit: str = Field(description="kg, W, m or a (years)")
    source: MeasureSource


class MaterialInfo(BaseModel):
    name: str
    value: str
    source: MeasureSource


class Indicators(BaseModel):
    """Reference quantities of a product, e.g. to state CO2eq per kg or per watt."""

    mass: Optional[Measure] = None
    power: Optional[Measure] = Field(default=None, description="Power consumption or rated power")
    lifetime: Optional[Measure] = Field(default=None, description="Service life in years")
    width: Optional[Measure] = None
    height: Optional[Measure] = None
    depth: Optional[Measure] = None
    volume: Optional[float] = Field(default=None, description="width × height × depth in m³")
    materials: list[MaterialInfo] = []
    warnings: list[str] = []
