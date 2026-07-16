from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.utils import base_object


def build_campaign(
    name: str,
    created: str,
    modified: str,
    labels: list[str] | None = None,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    clean = (name or "").strip()
    if not clean:
        raise ValueError("campaign name required")
    obj_id = stix_id("campaign", clean.lower())
    obj = base_object("campaign", obj_id, created, modified, labels=labels, marking_refs=marking_refs)
    obj["name"] = clean
    return obj
