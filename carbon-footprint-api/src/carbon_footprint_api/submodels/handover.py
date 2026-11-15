"""Parser für Handover Documentation: VDI 2770 1.0 (ZVEI), IDTA 02004 1.2 und 2.0 bis 2.0.4."""

from __future__ import annotations

from typing import Optional

from ..aas.model import AasObject
from .models import Classification, Document, DocumentId, DocumentVersion, FileRef, HandoverDocumentation, TemplateInfo
from .query import children, text, texts
from .registry import detect
from .structure import entries, flag, named, one, value

VDI = "http://admin-shell.io/vdi/2770/1/0/"
DOCUMENT = (VDI + "Document", "0173-1#02-ABI500")
DOCUMENT_VERSION = (VDI + "DocumentVersion", "0173-1#02-ABI503")


def _file(element: Optional[AasObject]) -> Optional[FileRef]:
    if element is None:
        return None
    if element.model_type == "File":
        path = text(element)
        return FileRef(path=path, contentType=element.get("contentType")) if path else None
    # 1.2: Collection mit DocumentPath und MimeType
    path = value(element, ["DocumentPath"])
    return FileRef(path=path, contentType=value(element, ["MimeType"])) if path else None


def _ids(doc: AasObject) -> list[DocumentId]:
    result = [
        DocumentId(
            domainId=value(item, ["DocumentDomainId"]),
            id=value(item, ["DocumentIdentifier", "ValueId", "DocumentId"]),
            isPrimary=flag(one(item, ["DocumentIsPrimary", "IsPrimary"])),
        )
        for _, item in entries(doc, ["DocumentIds"], ["DocumentId"])
        if item.model_type == "SubmodelElementCollection"
    ]
    # VDI 2770 1.0: DocumentId und IsPrimaryDocumentId direkt im Dokument
    flat = one(doc, ["DocumentId"])
    if flat is not None and flat.model_type == "Property":
        result.append(DocumentId(id=text(flat), isPrimary=flag(one(doc, ["IsPrimaryDocumentId", "IsPrimary"]))))
    return result


def _classifications(doc: AasObject) -> list[Classification]:
    result = [
        Classification(
            classId=value(item, ["ClassId"]),
            className=value(item, ["ClassName"]),
            system=value(item, ["ClassificationSystem"]),
        )
        for _, item in entries(doc, ["DocumentClassifications"], ["DocumentClassification"])
    ]
    if one(doc, ["DocumentClassId", "ClassId"]) is not None:  # VDI 2770 1.0: Merkmale direkt im Dokument
        result.append(
            Classification(
                classId=value(doc, ["DocumentClassId", "ClassId"]),
                className=value(doc, ["DocumentClassName", "ClassName"]),
                system=value(doc, ["DocumentClassificationSystem", "ClassificationSystem"]),
            )
        )
    return result


def _version(item: AasObject) -> DocumentVersion:
    languages: list[str] = []
    for lang in named(item, ["Language", "Languages"]):
        languages.extend(texts(lang))
    files = [_file(f) for f in named(item, ["DigitalFile"])]
    for lst in named(item, ["DigitalFiles"]):
        files.extend(_file(f) for f in children(lst))
    return DocumentVersion(
        languages=languages,
        version=value(item, ["Version", "DocumentVersionId"]),
        title=value(item, ["Title"]),
        subtitle=value(item, ["Subtitle", "SubTitle"]),
        description=value(item, ["Description", "Summary"]),
        keywords=value(item, ["KeyWords", "Keywords"]),
        statusSetDate=value(item, ["StatusSetDate", "SetDate"]),
        statusValue=value(item, ["StatusValue"]),
        role=value(item, ["Role"]),
        organizationName=value(item, ["OrganizationShortName", "OrganizationName"]),
        organizationOfficialName=value(item, ["OrganizationOfficialName"]),
        digitalFiles=[f for f in files if f is not None],
        previewFile=_file(one(item, ["PreviewFile"])),
    )


def parse_handover_documentation(
    submodel: AasObject, info: Optional[TemplateInfo] = None
) -> Optional[HandoverDocumentation]:
    info = info or detect(submodel)
    if info.family != "handover-documentation":
        return None
    result = HandoverDocumentation(templateVersion=info.version or info.variant, submodelId=submodel.get("id"))
    for path, doc in entries(submodel, ["Documents"], ["Document"], DOCUMENT):
        document = Document(
            idShortPath=path,
            ids=_ids(doc),
            classifications=_classifications(doc),
            versions=[
                _version(v) for _, v in entries(doc, ["DocumentVersions"], ["DocumentVersion"], DOCUMENT_VERSION)
            ],
        )
        if document.ids or document.versions or document.classifications:
            result.documents.append(document)
    return result
