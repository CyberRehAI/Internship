from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.parser import extract_extra_fields
from app.stix.utils import base_object, external_reference, is_valid_uri, normalize_timestamp


def build_report(
    pulse: dict[str, Any],
    object_refs: list[str],
    marking_refs: list[str] | None = None,
    *,
    preserve_source: bool = False,
) -> dict[str, Any]:
    pulse_id = (pulse.get("pulse_id") or "").strip()
    title = (pulse.get("title") or f"OTX Pulse {pulse_id}").strip()
    created = normalize_timestamp(pulse.get("created"))
    modified = normalize_timestamp(pulse.get("modified"), fallback=created)
    obj_id = stix_id("report", pulse_id or title.lower())

    refs: list[dict[str, Any]] = []
    invalid_refs: list[str] = []
    for url in pulse.get("references") or []:
        if not isinstance(url, str):
            continue
        cleaned = url.strip()
        if not cleaned:
            continue
        if is_valid_uri(cleaned):
            refs.append(external_reference("AlienVault OTX", cleaned))
        else:
            invalid_refs.append(cleaned)
    if pulse_id:
        refs.append(
            external_reference(
                "AlienVault OTX",
                f"https://otx.alienvault.com/pulse/{pulse_id}",
                external_id=pulse_id,
            )
        )

    labels = [str(t) for t in (pulse.get("tags") or []) if t]
    industries = [str(i) for i in (pulse.get("industries") or []) if i]
    labels.extend(industries)

    obj = base_object("report", obj_id, created, modified, labels=labels, marking_refs=marking_refs)
    obj["name"] = title
    obj["description"] = pulse.get("description") or ""
    obj["published"] = created
    obj["report_types"] = ["threat-report"]
    obj["object_refs"] = sorted(set(object_refs))
    if refs:
        obj["external_references"] = refs

    obj["x_otx_pulse_id"] = pulse_id
    obj["x_otx_is_public"] = pulse.get("is_public", True)
    optional_values = {
        "x_otx_industries": industries,
        "x_otx_adversary": pulse.get("adversary") or "",
        "x_otx_campaign": pulse.get("campaign") or "",
        "x_otx_targeted_countries": [
            str(c) for c in (pulse.get("targeted_countries") or []) if c
        ],
        "x_otx_malware_families": [
            str(m) for m in (pulse.get("malware_families") or []) if m
        ],
        "x_otx_attack_ids": [str(a) for a in (pulse.get("attack_ids") or []) if a],
        "x_otx_threat_actors": [str(a) for a in (pulse.get("threat_actors") or []) if a],
    }
    obj.update({key: value for key, value in optional_values.items() if value})
    if invalid_refs:
        obj["x_otx_invalid_references"] = invalid_refs
    obj["x_otx_tlp"] = pulse.get("tlp") or "white"
    if preserve_source:
        extra = extract_extra_fields(pulse)
        obj["x_otx_source"] = pulse
        if extra:
            obj["x_otx_extra_fields"] = extra
    return obj
