from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

KNOWN_PULSE_FIELDS = {
    "pulse_id",
    "title",
    "description",
    "author",
    "created",
    "modified",
    "tlp",
    "is_public",
    "tags",
    "malware_families",
    "attack_ids",
    "threat_actors",
    "industries",
    "targeted_countries",
    "references",
    "adversary",
    "campaign",
    "iocs",
}


def iter_pulses(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
            if not isinstance(data, dict):
                raise ValueError(f"Expected object on line {line_no}")
            yield data


def extract_extra_fields(pulse: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in pulse.items() if k not in KNOWN_PULSE_FIELDS}
