from __future__ import annotations

from typing import Any

from app.crawler.types import PulseIocRecord, PulseRecord


def _as_list_str(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            if v is None:
                continue
            out.append(str(v))
        return out
    if isinstance(value, str):
        return [value]
    return [str(value)]


def _first_str(*values: Any) -> str:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def normalize_pulse_full(pulse: dict[str, Any]) -> PulseRecord:
    author = ""
    author_obj = pulse.get("author")
    if isinstance(author_obj, dict):
        author = _first_str(author_obj.get("username"), author_obj.get("name"))
    author = _first_str(pulse.get("author_name"), author, pulse.get("author"))

    targeted_countries = (
        pulse.get("targeted_countries")
        or pulse.get("targeted_country")
        or pulse.get("countries")
        or pulse.get("country")
        or []
    )

    rec: PulseRecord = {
        "pulse_id": _first_str(pulse.get("id")),
        "title": _first_str(pulse.get("name"), pulse.get("title")),
        "description": _first_str(pulse.get("description")),
        "author": author,
        "created": _first_str(pulse.get("created")),
        "modified": _first_str(pulse.get("modified")),
        "tlp": _first_str(pulse.get("TLP"), pulse.get("tlp")),
        "is_public": bool(pulse.get("public", pulse.get("is_public", True))),
        "tags": _as_list_str(pulse.get("tags")),
        "malware_families": _as_list_str(pulse.get("malware_families")),
        "attack_ids": _as_list_str(pulse.get("attack_ids")),
        "references": _as_list_str(pulse.get("references")),
        "industries": _as_list_str(pulse.get("industries")),
        "targeted_countries": _as_list_str(targeted_countries),
        "adversary": _first_str(pulse.get("adversary"), pulse.get("threat_actor"), pulse.get("actor")),
        "campaign": _first_str(pulse.get("campaign")),
    }

    # Optional fields vary across pulses; keep them if present.
    threat_actors = pulse.get("threat_actors") or pulse.get("threat_actor") or pulse.get("actors")
    rec["threat_actors"] = _as_list_str(threat_actors)

    return rec


def normalize_indicators(indicators: list[dict[str, Any]]) -> list[PulseIocRecord]:
    out: list[PulseIocRecord] = []
    for item in indicators:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "indicator": _first_str(item.get("indicator")),
                "type": _first_str(item.get("type")),
                "role": _first_str(item.get("role")),
                "description": _first_str(item.get("description")),
            }
        )
    return out

