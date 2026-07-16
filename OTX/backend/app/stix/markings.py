from __future__ import annotations

import json
from typing import Any

try:
    from stix2 import TLP_AMBER, TLP_GREEN, TLP_RED, TLP_WHITE
except ImportError:  # pragma: no cover - exercised when stix2 missing
    TLP_WHITE = TLP_GREEN = TLP_AMBER = TLP_RED = None


def _marking_dict(marking: Any) -> dict[str, Any]:
    return json.loads(marking.serialize())


TLP_MARKING_IDS: dict[str, str] = {}
TLP_MARKING_OBJECTS: dict[str, dict[str, Any]] = {}

if TLP_WHITE is not None:
    TLP_MARKING_OBJECTS = {
        "white": _marking_dict(TLP_WHITE),
        "clear": _marking_dict(TLP_WHITE),
        "green": _marking_dict(TLP_GREEN),
        "amber": _marking_dict(TLP_AMBER),
        "amber+strict": _marking_dict(TLP_AMBER),
        "red": _marking_dict(TLP_RED),
    }
    TLP_MARKING_IDS = {key: obj["id"] for key, obj in TLP_MARKING_OBJECTS.items()}


def normalize_tlp(value: str) -> str:
    tlp = (value or "white").strip().lower()
    if tlp in ("clear", ""):
        return "white"
    if tlp.startswith("amber"):
        return "amber"
    if tlp not in TLP_MARKING_IDS:
        return "white"
    return tlp


def tlp_marking_ref(tlp: str) -> str:
    return TLP_MARKING_IDS[normalize_tlp(tlp)]


def ensure_marking_definitions(used_tlp: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tlp in sorted(used_tlp):
        key = normalize_tlp(tlp)
        obj = TLP_MARKING_OBJECTS.get(key)
        if obj and obj["id"] not in seen:
            out.append(dict(obj))
            seen.add(obj["id"])
    if not out and TLP_MARKING_OBJECTS:
        white = dict(TLP_MARKING_OBJECTS["white"])
        out.append(white)
    return out
