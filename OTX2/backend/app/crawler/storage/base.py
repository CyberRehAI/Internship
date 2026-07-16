from __future__ import annotations

from typing import Protocol

from app.crawler.types import PulseRecord


class PulseStore(Protocol):
    def has_pulse(self, pulse_id: str) -> bool: ...

    def mark_seen(self, pulse_id: str) -> None: ...

    def append_pulse(self, record: PulseRecord) -> None: ...

