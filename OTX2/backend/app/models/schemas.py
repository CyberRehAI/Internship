from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["connected", "error"]
    otx_user: str | None = None
    latency_ms: float


class SearchResponse(BaseModel):
    query: str
    detected_type: str
    search_strategy: str
    indicator_result: dict | None
    pulses: list[dict]
    total_pulses: int


class IOCDumpRequest(BaseModel):
    pulse_ids: list[str] = Field(default_factory=list)
    search_query: str | None = None
    tags: list[str] = Field(default_factory=list)
    type_filter: str = "all"


class IOCRecord(BaseModel):
    type: str
    value: str
    description: str | None = None
    pulse_id: str | None = None
    pulse_name: str | None = None
    author: str | None = None
    created: str | None = None
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    malware_families: list[str] = Field(default_factory=list)
    attack_ids: list[str] = Field(default_factory=list)
    tlp: str | None = None
    related_pulses: list[dict] = Field(default_factory=list)
    related_pulse_count: int = 0


class PulseIntelligenceContext(BaseModel):
    pulse_id: str
    immediate_threat: str
    threat_summary: str | None = None
    pulse_name: str | None = None
    author: str | None = None
    created: str | None = None
    tlp: str | None = None
    tags: list[str] = Field(default_factory=list)
    adversary: str | None = None
    targeted_countries: list[str] = Field(default_factory=list)
    malware_families: list[str] = Field(default_factory=list)
    attack_ids: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


class IOCDumpResponse(BaseModel):
    iocs: list[IOCRecord]
    stats: dict
    pulses_processed: int
    pulse_contexts: list[PulseIntelligenceContext] = Field(default_factory=list)


class ExportRequest(BaseModel):
    iocs: list[IOCRecord]
    mode: Literal["basic", "extended"]
    format: Literal["csv", "json", "xlsx"]


class ExportResponse(BaseModel):
    export_id: str
    filename: str
    format: str
    mode: str
    ioc_count: int
    created_at: datetime
    download_url: str
