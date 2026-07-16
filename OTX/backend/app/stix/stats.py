from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.stix.types import ConversionError, ConversionStats


def write_stats(stats: ConversionStats, path: Path, *, output_bytes: int = 0) -> None:
    payload = stats.to_dict()
    payload["output_bytes"] = output_bytes
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_errors(errors: list[ConversionError], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for err in errors:
            handle.write(json.dumps(asdict(err), ensure_ascii=False))
            handle.write("\n")
