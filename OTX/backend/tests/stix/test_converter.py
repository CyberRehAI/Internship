import json
from pathlib import Path

import pytest

from app.stix.converter import convert_jsonl_to_stix, convert_jsonl_to_stix_jsonl_bundles
from app.stix.ids import stix_id
from app.stix.mapper import StixMapper
from app.stix.patterns import build_indicator_pattern, normalize_ioc_key


def test_stix_id_is_deterministic():
    a = stix_id("indicator", "domain:evil.com")
    b = stix_id("indicator", "domain:evil.com")
    c = stix_id("indicator", "domain:other.com")
    assert a == b
    assert a != c
    assert a.startswith("indicator--")


@pytest.mark.parametrize(
    "ioc_type,value,expected_fragment",
    [
        ("FileHash-MD5", "abc", "MD5"),
        ("domain", "evil.com", "domain-name:value"),
        ("URL", "http://evil.com", "url:value"),
        ("email", "a@b.com", "email-addr:value"),
        ("CVE", "CVE-2024-1234", "vulnerability:name"),
    ],
)
def test_pattern_mapping(ioc_type, value, expected_fragment):
    result = build_indicator_pattern(ioc_type, value)
    assert expected_fragment in result.pattern
    assert result.pattern.startswith("[")
    assert result.pattern.endswith("]")


def test_indicator_dedup_across_pulses():
    mapper = StixMapper()
    pulse_a = {
        "pulse_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "A",
        "description": "d",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": [],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "",
        "campaign": "",
        "iocs": [{"indicator": "evil.com", "type": "domain", "role": "", "description": ""}],
    }
    pulse_b = dict(pulse_a)
    pulse_b["pulse_id"] = "bbbbbbbbbbbbbbbbbbbbbbbb"
    mapper.map_pulse(pulse_a)
    mapper.map_pulse(pulse_b)
    indicators = [o for o in mapper.registry.all_objects() if o["type"] == "indicator"]
    assert len(indicators) == 1
    assert mapper.stats.iocs_processed == 2


def test_no_report_related_to_relationships():
    mapper = StixMapper()
    pulse = {
        "pulse_id": "dddddddddddddddddddddddd",
        "title": "Rel Test",
        "description": "d",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": ["Crux"],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "ActorX",
        "campaign": "",
        "iocs": [{"indicator": "evil.com", "type": "domain", "role": "", "description": ""}],
    }
    report = mapper.map_pulse(pulse)
    assert report["object_refs"]
    report_rels = [
        r
        for r in mapper.relationships
        if r.get("relationship_type") == "related-to" and r.get("source_ref") == report["id"]
    ]
    assert report_rels == []


def test_campaign_attributed_to_threat_actor():
    mapper = StixMapper()
    pulse = {
        "pulse_id": "eeeeeeeeeeeeeeeeeeeeeeee",
        "title": "Campaign Test",
        "description": "d",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": [],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "APT41",
        "campaign": "OperationX",
        "iocs": [],
    }
    mapper.map_pulse(pulse)
    attributed = [r for r in mapper.relationships if r.get("relationship_type") == "attributed-to"]
    assert len(attributed) == 1
    rel = attributed[0]
    assert rel["source_ref"].startswith("campaign--")
    assert rel["target_ref"].startswith("threat-actor--")


def test_preservation_x_otx_source(tmp_path: Path):
    pulse = {
        "pulse_id": "cccccccccccccccccccccccc",
        "title": "Test Pulse",
        "description": "desc",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": ["ransomware"],
        "malware_families": ["Crux"],
        "attack_ids": ["T1486"],
        "threat_actors": [],
        "industries": ["Finance"],
        "targeted_countries": ["United States of America"],
        "references": ["https://example.com/report"],
        "adversary": "ActorX",
        "campaign": "CampY",
        "iocs": [{"indicator": "1.2.3.4", "type": "IPv4", "role": "", "description": ""}],
        "custom_field": "preserve-me",
    }
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(json.dumps(pulse) + "\n", encoding="utf-8")
    output_path = tmp_path / "bundle.json"
    convert_jsonl_to_stix(input_path, output_path, validate=False, preserve_source=True)
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    reports = [o for o in bundle["objects"] if o["type"] == "report"]
    assert len(reports) == 1
    assert reports[0]["x_otx_source"]["custom_field"] == "preserve-me"
    assert reports[0]["x_otx_industries"] == ["Finance"]


def test_preserve_source_off_by_default(tmp_path: Path):
    pulse = {
        "pulse_id": "ffffffffffffffffffffffff",
        "title": "No Source",
        "description": "d",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": [],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "",
        "campaign": "",
        "iocs": [],
        "custom_field": "should-not-embed",
    }
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(json.dumps(pulse) + "\n", encoding="utf-8")
    output_path = tmp_path / "bundle.json"
    convert_jsonl_to_stix(input_path, output_path, validate=False)
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    reports = [o for o in bundle["objects"] if o["type"] == "report"]
    report = reports[0]
    assert "x_otx_source" not in report
    for key in (
        "x_otx_industries",
        "x_otx_adversary",
        "x_otx_campaign",
        "x_otx_targeted_countries",
        "x_otx_malware_families",
        "x_otx_attack_ids",
        "x_otx_threat_actors",
    ):
        assert key not in report


def test_normalize_ioc_key_case_insensitive():
    assert normalize_ioc_key("Domain", "Evil.COM") == normalize_ioc_key("domain", "evil.com")


def _sample_pulse(pulse_id: str, **overrides) -> dict:
    pulse = {
        "pulse_id": pulse_id,
        "title": f"Pulse {pulse_id[:8]}",
        "description": "d",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": ["Crux"],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "",
        "campaign": "",
        "iocs": [{"indicator": "evil.com", "type": "domain", "role": "", "description": ""}],
    }
    pulse.update(overrides)
    return pulse


def test_per_pulse_jsonl_bundles_one_line_per_pulse(tmp_path: Path):
    pulse_a = _sample_pulse("aaaaaaaaaaaaaaaaaaaaaaaa")
    pulse_b = _sample_pulse("bbbbbbbbbbbbbbbbbbbbbbbb")
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(
        json.dumps(pulse_a) + "\n" + json.dumps(pulse_b) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "bundles.jsonl"
    summary = convert_jsonl_to_stix_jsonl_bundles(input_path, output_path, validate=False)

    lines = [line for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert summary["bundles_written"] == 2
    assert summary["output_format"] == "bundle-jsonl"

    for line in lines:
        bundle = json.loads(line)
        assert bundle["type"] == "bundle"
        assert bundle["id"].startswith("bundle--")
        assert isinstance(bundle["objects"], list)
        reports = [o for o in bundle["objects"] if o["type"] == "report"]
        assert len(reports) == 1
        markings = [o for o in bundle["objects"] if o["type"] == "marking-definition"]
        assert markings


def test_per_pulse_jsonl_no_cross_pulse_dedup(tmp_path: Path):
    pulse_a = _sample_pulse("cccccccccccccccccccccccc")
    pulse_b = _sample_pulse("dddddddddddddddddddddddd")
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(
        json.dumps(pulse_a) + "\n" + json.dumps(pulse_b) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "bundles.jsonl"
    convert_jsonl_to_stix_jsonl_bundles(input_path, output_path, validate=False)

    bundles = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    malware_per_bundle = [
        [o for o in bundle["objects"] if o["type"] == "malware"] for bundle in bundles
    ]
    assert len(malware_per_bundle[0]) == 1
    assert len(malware_per_bundle[1]) == 1
    assert malware_per_bundle[0][0]["id"] == malware_per_bundle[1][0]["id"]
