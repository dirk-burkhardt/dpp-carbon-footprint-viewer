"""Parser für Typenschilder: ZVEI Nameplate 1.0, Digital Nameplate 2.0 und 3.0, Battery Passport, HSU."""

from __future__ import annotations

from typing import Optional

from ..aas.model import AasObject
from .address import parse_address
from .models import Nameplate, TemplateInfo
from .query import find, text
from .registry import detect

CONTACT = "https://admin-shell.io/zvei/nameplate/1/0/ContactInformations/"
NAMEPLATE_FAMILIES = ("nameplate", "battery-nameplate")

_ADDRESS = (
    (
        CONTACT + "ContactInformation",
        CONTACT + "AddressInformation",
        "0173-1#02-AAQ832",  # Address (Nameplate 1.0)
        "https://www.hsu-hh.de/aut/aas/physicaladdress",
    ),
    ("ContactInformation", "AddressInformation", "Address", "PhysicalAddress"),
)
_FIELDS = {
    "manufacturerName": (("0173-1#02-AAO677", "0112/2///61987#ABA565"), ("ManufacturerName",)),
    "productDesignation": (("0173-1#02-AAW338", "0112/2///61987#ABA567"), ("ManufacturerProductDesignation",)),
    "productFamily": (("0173-1#02-AAU731", "0112/2///61987#ABP464"), ("ManufacturerProductFamily",)),
    "serialNumber": (("0173-1#02-AAM556", "0112/2///61987#ABA951"), ("SerialNumber",)),
    "yearOfConstruction": (("0173-1#02-AAP906", "0112/2///61987#ABP000"), ("YearOfConstruction",)),
    "countryOfOrigin": (("0173-1#02-AAO259", "0112/2///61987#ABP462"), ("CountryOfOrigin",)),
}


def parse_nameplate(submodel: AasObject, info: Optional[TemplateInfo] = None) -> Optional[Nameplate]:
    info = info or detect(submodel)
    if info.family not in NAMEPLATE_FAMILIES:
        return None
    result = Nameplate(templateVersion=info.version or info.variant, submodelId=submodel.get("id"))
    for name, (sids, shorts) in _FIELDS.items():
        setattr(result, name, text(find(submodel, sids, shorts)))
    result.address = parse_address(find(submodel, *_ADDRESS))
    return result
