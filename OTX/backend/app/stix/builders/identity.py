from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.utils import base_object, external_reference, normalize_timestamp


def build_identity(
    author: str,
    created: str,
    modified: str,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    name = (author or "Unknown").strip() or "Unknown"
    obj_id = stix_id("identity", name.lower())
    obj = base_object("identity", obj_id, created, modified, marking_refs=marking_refs)
    obj["name"] = name
    obj["identity_class"] = "organization" if name.lower() in {"alienvault", "levelblue", "otx"} else "individual"
    obj["x_otx_author"] = author
    return obj
