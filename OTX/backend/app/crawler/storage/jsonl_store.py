from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.crawler.types import PulseRecord
from app.crawler.utils import append_jsonl, append_line, ensure_parent_dir


@dataclass
class JsonlPulseStore:
    out_path: Path
    seen_ids_path: Path

    def __post_init__(self) -> None:
        ensure_parent_dir(self.out_path)
        ensure_parent_dir(self.seen_ids_path)
        self._seen: set[str] = set()
        if self.seen_ids_path.exists():
            for line in self.seen_ids_path.read_text(encoding="utf-8").splitlines():
                pulse_id = line.strip()
                if pulse_id:
                    self._seen.add(pulse_id)

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    def has_pulse(self, pulse_id: str) -> bool:
        return pulse_id in self._seen

    def append_pulse(self, record: PulseRecord) -> None:
        pulse_id = (record.get("pulse_id") or "").strip()
        if not pulse_id:
            return
        if pulse_id in self._seen:
            return

        append_jsonl(self.out_path, record)
        append_line(self.seen_ids_path, pulse_id)
        self._seen.add(pulse_id)

