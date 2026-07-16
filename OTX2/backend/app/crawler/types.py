from __future__ import annotations

from typing import Any, Literal, TypedDict


class PulseIocRecord(TypedDict, total=False):
    indicator: str
    type: str
    role: str
    description: str


class PulseRecord(TypedDict, total=False):
    pulse_id: str
    title: str
    description: str
    author: str
    created: str
    modified: str
    tlp: str
    is_public: bool

    tags: list[str]
    malware_families: list[str]
    attack_ids: list[str]
    threat_actors: list[str]
    industries: list[str]
    targeted_countries: list[str]
    references: list[str]
    adversary: str
    campaign: str

    iocs: list[PulseIocRecord]


Mode = Literal["full", "update"]


class CrawlCheckpoint(TypedDict, total=False):
    last_page: int
    last_index_in_page: int
    written_pulses: int
    skipped_pulses: int
    failed_pulses: int
    mode: Mode
    updated_at: str


class CrawlErrorRecord(TypedDict, total=False):
    pulse_id: str
    page: int
    index_in_page: int
    attempt: int
    error: str
    message: str
    timestamp: str
    endpoint: str
    extra: dict[str, Any]

