from __future__ import annotations

from typing import Any

from app.stix.ids import relationship_id
from app.stix.utils import normalize_timestamp, utc_now


def build_relationship(
    source_id: str,
    relationship_type: str,
    target_id: str,
    created: str | None = None,
    modified: str | None = None,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    ts = normalize_timestamp(created) if created else utc_now()
    mod = normalize_timestamp(modified, fallback=ts)
    obj_id = relationship_id(source_id, relationship_type, target_id)
    obj: dict[str, Any] = {
        "type": "relationship",
        "spec_version": "2.1",
        "id": obj_id,
        "created": ts,
        "modified": mod,
        "relationship_type": relationship_type,
        "source_ref": source_id,
        "target_ref": target_id,
    }
    if marking_refs:
        obj["object_marking_refs"] = marking_refs
    return obj
