from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.patterns import PatternResult, build_indicator_pattern, normalize_ioc_key
from app.stix.utils import base_object, normalize_timestamp, utc_now


def build_indicator(
    ioc_type: str,
    value: str,
    *,
    role: str = "",
    description: str = "",
    created: str | None = None,
    modified: str | None = None,
    labels: list[str] | None = None,
    marking_refs: list[str] | None = None,
    pulse_id: str = "",
) -> tuple[dict[str, Any], PatternResult]:
    key = normalize_ioc_key(ioc_type, value)
    obj_id = stix_id("indicator", key)
    ts = normalize_timestamp(created) if created else utc_now()
    mod = normalize_timestamp(modified, fallback=ts)
    pattern_result = build_indicator_pattern(ioc_type, value)

    obj = base_object("indicator", obj_id, ts, mod, labels=labels, marking_refs=marking_refs)
    obj["name"] = f"{ioc_type}: {value}"[:250]
    obj["pattern"] = pattern_result.pattern
    obj["pattern_type"] = pattern_result.pattern_type
    obj["valid_from"] = ts
    obj["indicator_types"] = ["malicious-activity"]
    obj["x_otx_indicator_type"] = ioc_type
    obj["x_otx_original_value"] = value
    if role:
        obj["x_otx_role"] = role
    if description:
        obj["description"] = description
        obj["x_otx_description"] = description
    if pulse_id:
        obj["x_otx_pulse_id"] = pulse_id
    if pattern_result.fallback:
        obj["x_otx_pattern_fallback"] = True
    if pattern_result.yara_reclassified:
        obj["x_otx_yara_reclassified"] = True
    return obj, pattern_result
