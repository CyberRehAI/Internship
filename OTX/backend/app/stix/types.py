from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversionError:
    pulse_id: str
    ioc_index: int | None
    error: str
    message: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionStats:
    pulses_processed: int = 0
    iocs_processed: int = 0
    iocs_skipped: int = 0
    objects_by_type: dict[str, int] = field(default_factory=dict)
    relationships: int = 0
    relationships_by_type: dict[str, int] = field(default_factory=dict)
    warnings: int = 0
    errors: int = 0

    def bump_type(self, stix_type: str) -> None:
        self.objects_by_type[stix_type] = self.objects_by_type.get(stix_type, 0) + 1

    def bump_relationship(self, relationship_type: str) -> None:
        self.relationships_by_type[relationship_type] = (
            self.relationships_by_type.get(relationship_type, 0) + 1
        )

    def merge_from(self, other: ConversionStats) -> None:
        self.pulses_processed += other.pulses_processed
        self.iocs_processed += other.iocs_processed
        self.iocs_skipped += other.iocs_skipped
        self.relationships += other.relationships
        self.warnings += other.warnings
        self.errors += other.errors
        for stix_type, count in other.objects_by_type.items():
            self.objects_by_type[stix_type] = self.objects_by_type.get(stix_type, 0) + count
        for rel_type, count in other.relationships_by_type.items():
            self.relationships_by_type[rel_type] = self.relationships_by_type.get(rel_type, 0) + count

    def to_dict(self) -> dict[str, Any]:
        return {
            "pulses_processed": self.pulses_processed,
            "iocs_processed": self.iocs_processed,
            "iocs_skipped": self.iocs_skipped,
            "objects_by_type": dict(sorted(self.objects_by_type.items())),
            "relationships": self.relationships,
            "relationships_by_type": dict(sorted(self.relationships_by_type.items())),
            "warnings": self.warnings,
            "errors": self.errors,
            "total_objects": sum(self.objects_by_type.values()),
        }
