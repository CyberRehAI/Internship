from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.utils import base_object

# Common OTX country names -> ISO 3166-1 alpha-2 (best effort).
COUNTRY_NAME_TO_ISO: dict[str, str] = {
    "united states of america": "US",
    "united states": "US",
    "usa": "US",
    "united kingdom of great britain and northern ireland": "GB",
    "united kingdom": "GB",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "israel": "IL",
    "india": "IN",
    "china": "CN",
    "russian federation": "RU",
    "russia": "RU",
    "japan": "JP",
    "south africa": "ZA",
    "central african republic": "CF",
    "brazil": "BR",
    "mexico": "MX",
    "singapore": "SG",
    "hong kong": "HK",
    "taiwan": "TW",
}


def build_location(
    country_name: str,
    created: str,
    modified: str,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    clean = (country_name or "").strip()
    if not clean:
        raise ValueError("country name required")
    obj_id = stix_id("location", clean.lower())
    obj = base_object("location", obj_id, created, modified, marking_refs=marking_refs)
    obj["name"] = clean
    iso = COUNTRY_NAME_TO_ISO.get(clean.lower())
    if iso:
        obj["country"] = iso
    else:
        obj["region"] = clean
    obj["x_otx_country_name"] = clean
    return obj
