"""Adressen aus Carbon Footprint (0.9: eigene IRDIs, 1.0: AddressInformation) und Nameplate/Contact Information."""

from __future__ import annotations

from typing import Optional

from ..aas.model import AasObject
from .models import Address
from .query import find, number, text

HSU = "https://www.hsu-hh.de/aut/aas/"

# Feld: (SemanticIds, idShorts). Reihenfolge der SemanticIds: Carbon Footprint 0.9, Contact Information, HSU
_FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "street": (("0173-1#02-ABH956", "0173-1#02-AAO128", HSU + "street"), ("Street",)),
    "houseNumber": (("0173-1#02-ABH957",), ("HouseNumber",)),
    "zipcode": (("0173-1#02-ABH958", "0173-1#02-AAO129", HSU + "postalcode"), ("Zipcode", "ZipCode", "PostalCode")),
    "cityTown": (("0173-1#02-ABH959", "0173-1#02-AAO132", HSU + "city"), ("CityTown", "City")),
    "stateCounty": (("0173-1#02-AAO133", HSU + "statecounty"), ("StateCounty",)),
    "country": (
        ("0173-1#02-AAO259", "0173-1#02-AAO134", "0173-1#02-AAO730"),
        ("Country", "NationalCode", "CountryCode"),
    ),
}
_COORDINATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "latitude": (("0173-1#02-ABH960",), ("Latitude",)),
    "longitude": (("0173-1#02-ABH961",), ("Longitude",)),
}


def parse_address(collection: Optional[AasObject]) -> Optional[Address]:
    """Adresse aus einer Collection; ``None``, wenn sie fehlt oder leer ist."""
    if collection is None:
        return None
    values: dict[str, object] = {}
    for name, (sids, shorts) in _FIELDS.items():
        values[name] = text(find(collection, sids, shorts))
    for name, (sids, shorts) in _COORDINATES.items():
        values[name] = number(find(collection, sids, shorts))
    address = Address.model_validate(values)
    return None if address.is_empty() else address
