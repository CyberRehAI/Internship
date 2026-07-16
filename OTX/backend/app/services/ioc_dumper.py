from collections import Counter
import re

from app.core.exceptions import OTXBadRequestError
from app.services.pulse_service import PulseService

FILTER_MAP = {
    "ip": {"IPv4", "IPv6", "CIDR"},
    "domains": {"domain", "hostname"},
    "urls": {"URL", "URI"},
    "file_hashes": {"FileHash-MD5", "FileHash-SHA1", "FileHash-SHA256"},
    "cves": {"CVE"},
    "email_addresses": {"email"},
    "yara": {"YARA"},
    "all": None,
}


def _normalize_type(value: str) -> str:
    return (value or "").strip()


PULSE_ID_PATTERN = re.compile(r"^[0-9A-Za-z]{24}$")


def _normalize_pulse_id(value: str) -> str:
    return (value or "").strip()


class IOCDumperService:
    def __init__(self, pulse_service: PulseService) -> None:
        self.pulse_service = pulse_service

    def dump(
        self,
        pulse_ids: list[str],
        search_query: str | None,
        tags: list[str],
        type_filter: str,
        max_search_pulses: int = 25,
    ) -> tuple[list[dict], dict, int, list[dict]]:
        pulse_map: dict[str, dict] = {}
        normalized_pulse_ids = [_normalize_pulse_id(pulse_id) for pulse_id in pulse_ids if _normalize_pulse_id(pulse_id)]
        invalid_pulse_ids = [pulse_id for pulse_id in normalized_pulse_ids if not PULSE_ID_PATTERN.match(pulse_id)]
        if invalid_pulse_ids:
            raise OTXBadRequestError(
                "Invalid pulse_id format. Pulse IDs must be 24 alphanumeric characters. "
                f"Invalid values: {', '.join(invalid_pulse_ids)}"
            )

        for pulse_id in normalized_pulse_ids:
            pulse_map[pulse_id] = self.pulse_service.get_details(pulse_id)

        if search_query:
            for pulse in self.pulse_service.search(search_query, limit=max_search_pulses):
                if tags and not set(tags).intersection(set(pulse.get("tags", []))):
                    continue
                if pulse.get("id"):
                    pulse_map[pulse["id"]] = pulse

        dedup: dict[tuple[str, str], dict] = {}
        related_pulses_by_key: dict[tuple[str, str], dict[str, dict]] = {}
        for pulse in pulse_map.values():
            current_pulse_id = pulse.get("id")
            if not current_pulse_id:
                continue
            indicators = self.pulse_service.get_indicators(current_pulse_id)
            for indicator in indicators:
                record = {
                    "type": indicator.get("type"),
                    "value": indicator.get("indicator"),
                    "description": indicator.get("description"),
                    "pulse_id": current_pulse_id,
                    "pulse_name": pulse.get("name"),
                    "author": pulse.get("author_name"),
                    "created": pulse.get("created"),
                    "tags": pulse.get("tags", []),
                    "references": pulse.get("references", []),
                    "malware_families": pulse.get("malware_families", []),
                    "attack_ids": pulse.get("attack_ids", []),
                    "tlp": pulse.get("TLP"),
                }
                record_type = _normalize_type(record["type"])
                record_value = str(record["value"] or "").strip().lower()
                key = (record_type, record_value)
                related_pulses_by_key.setdefault(key, {})
                related_pulses_by_key[key][current_pulse_id] = {
                    "pulse_id": current_pulse_id,
                    "pulse_name": pulse.get("name"),
                }
                existing = dedup.get(key)
                if existing is None or len(existing.get("references", [])) < len(record.get("references", [])):
                    dedup[key] = record

        iocs = list(dedup.values())
        for ioc in iocs:
            key = (_normalize_type(ioc.get("type")), str(ioc.get("value") or "").strip().lower())
            related = list(related_pulses_by_key.get(key, {}).values())
            ioc["related_pulses"] = related
            ioc["related_pulse_count"] = len(related)
        allowed_types = FILTER_MAP.get(type_filter.lower(), None)
        if allowed_types:
            iocs = [ioc for ioc in iocs if ioc.get("type") in allowed_types]

        by_type = Counter((item.get("type") or "unknown") for item in iocs)
        stats = {"by_type": dict(by_type), "total": len(iocs), "unique": len(iocs)}
        pulse_contexts = []
        for pulse in pulse_map.values():
            immediate_threat = pulse.get("name") or "OTX pulse threat observed"
            pulse_contexts.append(
                {
                    "pulse_id": pulse.get("id"),
                    "immediate_threat": immediate_threat,
                    "threat_summary": pulse.get("description"),
                    "pulse_name": pulse.get("name"),
                    "author": pulse.get("author_name"),
                    "created": pulse.get("created"),
                    "tlp": pulse.get("TLP"),
                    "tags": pulse.get("tags", []),
                    "adversary": pulse.get("adversary"),
                    "targeted_countries": pulse.get("targeted_countries", []),
                    "malware_families": pulse.get("malware_families", []),
                    "attack_ids": pulse.get("attack_ids", []),
                    "references": pulse.get("references", []),
                }
            )
        return iocs, stats, len(pulse_map), pulse_contexts
