from __future__ import annotations

import logging
from typing import Any

from app.stix.builders.attack_pattern import build_attack_pattern
from app.stix.builders.campaign import build_campaign
from app.stix.builders.identity import build_identity
from app.stix.builders.indicator import build_indicator
from app.stix.builders.location import build_location
from app.stix.builders.malware import build_malware
from app.stix.builders.report import build_report
from app.stix.builders.threat_actor import build_threat_actor
from app.stix.builders.vulnerability import build_vulnerability
from app.stix.markings import normalize_tlp, tlp_marking_ref
from app.stix.patterns import normalize_ioc_key
from app.stix.registry import EntityRegistry
from app.stix.relationships import build_relationship
from app.stix.types import ConversionError, ConversionStats
from app.stix.utils import normalize_timestamp

logger = logging.getLogger(__name__)


class StixMapper:
    def __init__(self, *, preserve_source: bool = False) -> None:
        self.preserve_source = preserve_source
        self.registry = EntityRegistry()
        self.relationships: list[dict[str, Any]] = []
        self.relationship_keys: set[str] = set()
        self.used_tlp: set[str] = set()
        self.stats = ConversionStats()
        self.errors: list[ConversionError] = []

    def _marking_refs(self, tlp: str) -> list[str]:
        self.used_tlp.add(normalize_tlp(tlp))
        return [tlp_marking_ref(tlp)]

    def _add_relationship(
        self,
        source_id: str,
        rel_type: str,
        target_id: str,
        created: str,
        modified: str,
        marking_refs: list[str],
    ) -> None:
        key = f"{source_id}|{rel_type}|{target_id}"
        if key in self.relationship_keys:
            return
        self.relationship_keys.add(key)
        rel = build_relationship(source_id, rel_type, target_id, created, modified, marking_refs)
        self.relationships.append(rel)
        self.stats.relationships += 1
        self.stats.bump_relationship(rel_type)
        self.stats.bump_type("relationship")

    def _link_campaign_relationships(
        self,
        campaign_id: str | None,
        actor_ids: list[str],
        location_ids: list[str],
        created: str,
        modified: str,
        marking_refs: list[str],
    ) -> None:
        if not campaign_id:
            return
        for actor_id in actor_ids:
            self._add_relationship(campaign_id, "attributed-to", actor_id, created, modified, marking_refs)
        for location_id in location_ids:
            self._add_relationship(campaign_id, "targets", location_id, created, modified, marking_refs)

    def _register_entity(self, key: str, obj: dict[str, Any]) -> dict[str, Any]:
        registered = self.registry.register(key, obj)
        if registered["id"] == obj["id"]:
            self.stats.bump_type(obj["type"])
        return registered

    def _get_or_create_identity(self, author: str, created: str, modified: str, marking_refs: list[str]) -> dict[str, Any]:
        name = (author or "Unknown").strip() or "Unknown"
        key = f"identity:{name.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            return existing
        obj = build_identity(name, created, modified, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_malware(
        self, name: str, created: str, modified: str, labels: list[str], marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"malware:{name.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            self.registry.merge_labels(existing["id"], labels)
            return existing
        obj = build_malware(name, created, modified, labels, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_threat_actor(
        self, name: str, created: str, modified: str, labels: list[str], marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"threat-actor:{name.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            self.registry.merge_labels(existing["id"], labels)
            return existing
        obj = build_threat_actor(name, created, modified, labels, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_campaign(
        self, name: str, created: str, modified: str, labels: list[str], marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"campaign:{name.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            return existing
        obj = build_campaign(name, created, modified, labels, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_attack_pattern(
        self, attack_id: str, created: str, modified: str, labels: list[str], marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"attack-pattern:{attack_id.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            return existing
        obj = build_attack_pattern(attack_id, created, modified, labels, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_location(
        self, country: str, created: str, modified: str, marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"location:{country.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            return existing
        obj = build_location(country, created, modified, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_vulnerability(
        self, cve_id: str, created: str, modified: str, marking_refs: list[str]
    ) -> dict[str, Any]:
        key = f"vulnerability:{cve_id.lower()}"
        existing = self.registry.get_by_key(key)
        if existing:
            return existing
        obj = build_vulnerability(cve_id, created, modified, marking_refs)
        return self._register_entity(key, obj)

    def _get_or_create_indicator(
        self,
        ioc: dict[str, Any],
        pulse: dict[str, Any],
        labels: list[str],
        marking_refs: list[str],
    ) -> dict[str, Any] | None:
        ioc_type = str(ioc.get("type") or "").strip()
        value = str(ioc.get("indicator") or "").strip()
        if not value:
            return None
        key = f"indicator:{normalize_ioc_key(ioc_type, value)}"
        existing = self.registry.get_by_key(key)
        if existing:
            self.registry.merge_labels(existing["id"], labels)
            return existing
        created = normalize_timestamp(pulse.get("created"))
        modified = normalize_timestamp(pulse.get("modified"), fallback=created)
        obj, pattern_result = build_indicator(
            ioc_type,
            value,
            role=str(ioc.get("role") or ""),
            description=str(ioc.get("description") or ""),
            created=created,
            modified=modified,
            labels=labels,
            marking_refs=marking_refs,
            pulse_id=str(pulse.get("pulse_id") or ""),
        )
        if pattern_result.fallback:
            self.stats.warnings += 1
        return self._register_entity(key, obj)

    def map_pulse(self, pulse: dict[str, Any]) -> dict[str, Any]:
        pulse_id = str(pulse.get("pulse_id") or "")
        created = normalize_timestamp(pulse.get("created"))
        modified = normalize_timestamp(pulse.get("modified"), fallback=created)
        tlp = str(pulse.get("tlp") or "white")
        marking_refs = self._marking_refs(tlp)
        labels = [str(t) for t in (pulse.get("tags") or []) if t]

        related_ids: list[str] = []

        try:
            identity = self._get_or_create_identity(str(pulse.get("author") or ""), created, modified, marking_refs)
            related_ids.append(identity["id"])
        except Exception as exc:
            self._record_error(pulse_id, None, "identity_build", str(exc))

        actor_names: list[str] = []
        if pulse.get("adversary"):
            actor_names.append(str(pulse["adversary"]))
        for name in pulse.get("threat_actors") or []:
            if name:
                actor_names.append(str(name))
        actor_ids: list[str] = []
        for name in sorted(set(actor_names)):
            try:
                actor = self._get_or_create_threat_actor(name, created, modified, labels, marking_refs)
                actor_ids.append(actor["id"])
                related_ids.append(actor["id"])
            except Exception as exc:
                self._record_error(pulse_id, None, "threat_actor_build", str(exc))

        campaign_id: str | None = None
        campaign_name = str(pulse.get("campaign") or "").strip()
        if campaign_name:
            try:
                campaign = self._get_or_create_campaign(campaign_name, created, modified, labels, marking_refs)
                campaign_id = campaign["id"]
                related_ids.append(campaign_id)
            except Exception as exc:
                self._record_error(pulse_id, None, "campaign_build", str(exc))

        malware_ids: list[str] = []
        for family in pulse.get("malware_families") or []:
            if not family:
                continue
            try:
                malware = self._get_or_create_malware(str(family), created, modified, labels, marking_refs)
                malware_ids.append(malware["id"])
                related_ids.append(malware["id"])
            except Exception as exc:
                self._record_error(pulse_id, None, "malware_build", str(exc))

        attack_ids: list[str] = []
        for attack_id in pulse.get("attack_ids") or []:
            if not attack_id:
                continue
            try:
                ap = self._get_or_create_attack_pattern(str(attack_id), created, modified, labels, marking_refs)
                attack_ids.append(ap["id"])
                related_ids.append(ap["id"])
            except Exception as exc:
                self._record_error(pulse_id, None, "attack_pattern_build", str(exc))

        location_ids: list[str] = []
        for country in pulse.get("targeted_countries") or []:
            if not country:
                continue
            try:
                loc = self._get_or_create_location(str(country), created, modified, marking_refs)
                location_ids.append(loc["id"])
                related_ids.append(loc["id"])
            except Exception as exc:
                self._record_error(pulse_id, None, "location_build", str(exc))

        indicator_ids: list[str] = []
        vulnerability_ids: list[str] = []
        for idx, ioc in enumerate(pulse.get("iocs") or []):
            if not isinstance(ioc, dict):
                continue
            try:
                indicator = self._get_or_create_indicator(ioc, pulse, labels, marking_refs)
                if indicator is None:
                    self.stats.iocs_skipped += 1
                    continue
                indicator_ids.append(indicator["id"])
                related_ids.append(indicator["id"])
                self.stats.iocs_processed += 1

                ioc_type = str(ioc.get("type") or "").strip().upper()
                if ioc_type == "CVE":
                    cve = self._get_or_create_vulnerability(str(ioc.get("indicator") or ""), created, modified, marking_refs)
                    vulnerability_ids.append(cve["id"])
                    related_ids.append(cve["id"])
            except Exception as exc:
                self.stats.iocs_skipped += 1
                self._record_error(pulse_id, idx, "indicator_build", str(exc))

        report = build_report(pulse, related_ids, marking_refs, preserve_source=self.preserve_source)
        self._register_entity(f"report:{pulse_id}", report)

        for indicator_id in indicator_ids:
            for malware_id in malware_ids:
                self._add_relationship(indicator_id, "indicates", malware_id, created, modified, marking_refs)

        for actor_id in actor_ids:
            for malware_id in malware_ids:
                self._add_relationship(actor_id, "uses", malware_id, created, modified, marking_refs)

        for malware_id in malware_ids:
            for attack_id_ref in attack_ids:
                self._add_relationship(malware_id, "uses", attack_id_ref, created, modified, marking_refs)

        self._link_campaign_relationships(
            campaign_id, actor_ids, location_ids, created, modified, marking_refs
        )

        self.stats.pulses_processed += 1
        return report

    def _record_error(self, pulse_id: str, ioc_index: int | None, error: str, message: str) -> None:
        self.stats.errors += 1
        self.errors.append(ConversionError(pulse_id=pulse_id, ioc_index=ioc_index, error=error, message=message))
