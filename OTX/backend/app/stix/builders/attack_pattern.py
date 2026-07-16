from __future__ import annotations

from typing import Any

from app.stix.ids import stix_id
from app.stix.patterns import parse_mitre_technique_id
from app.stix.utils import base_object, external_reference


def build_attack_pattern(
    attack_id: str,
    created: str,
    modified: str,
    labels: list[str] | None = None,
    marking_refs: list[str] | None = None,
) -> dict[str, Any]:
    technique = parse_mitre_technique_id(attack_id) or attack_id.strip()
    obj_id = stix_id("attack-pattern", technique.lower())
    obj = base_object("attack-pattern", obj_id, created, modified, labels=labels, marking_refs=marking_refs)
    obj["name"] = technique
    obj["external_references"] = [
        external_reference(
            "mitre-attack",
            f"https://attack.mitre.org/techniques/{technique.replace('.', '/')}/",
            external_id=technique,
        )
    ]
    return obj
