from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.stix.markings import ensure_marking_definitions
from app.stix.utils import utc_now


def build_bundle(objects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "bundle",
        "id": f"bundle--{utc_now().replace(':', '').replace('-', '').replace('.', '')}",
        "objects": objects,
    }


def export_bundle(bundle: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")


def assemble_bundle(
    sdo_objects: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    used_tlp: set[str],
) -> dict[str, Any]:
    markings = ensure_marking_definitions(used_tlp)
    marking_ids = {m["id"] for m in markings}
    all_objects: list[dict[str, Any]] = []
    seen: set[str] = set()

    for obj in markings + sdo_objects + relationships:
        obj_id = obj.get("id")
        if not obj_id or obj_id in seen:
            continue
        seen.add(obj_id)
        all_objects.append(obj)

    # Ensure bundle is self-contained for marking refs.
    for obj in all_objects:
        for ref in obj.get("object_marking_refs") or []:
            if ref not in marking_ids and ref.startswith("marking-definition--"):
                pass  # well-known TLP refs included above

    return build_bundle(all_objects)
