from app.stix.builders.indicator import build_indicator
from app.stix.mapper import StixMapper
from app.stix.patterns import build_indicator_pattern, detect_file_hash, is_yara_rule


def test_is_yara_rule_detects_real_rule():
    rule = """rule ExampleRule {
    meta:
        author = "test"
    strings:
        $a = "malware"
    condition:
        $a
}"""
    assert is_yara_rule(rule)


def test_is_yara_rule_rejects_sha1_hash():
    assert not is_yara_rule("d83494bd8a7f816ce39576c776e67c2e9f568080")


def test_detect_file_hash_lengths():
    assert detect_file_hash("a" * 32) == "FileHash-MD5"
    assert detect_file_hash("d83494bd8a7f816ce39576c776e67c2e9f568080") == "FileHash-SHA1"
    assert detect_file_hash("a" * 64) == "FileHash-SHA256"
    assert detect_file_hash("not-a-hash") is None


def test_yara_sha1_reclassified_to_stix_hash_pattern():
    result = build_indicator_pattern("YARA", "d83494bd8a7f816ce39576c776e67c2e9f568080")
    assert result.pattern_type == "stix"
    assert "SHA-1" in result.pattern
    assert result.yara_reclassified


def test_yara_real_rule_keeps_yara_pattern_type():
    rule = """rule ExampleRule {
    strings:
        $a = "test"
    condition:
        $a
}"""
    result = build_indicator_pattern("YARA", rule)
    assert result.pattern_type == "yara"
    assert result.pattern == rule
    assert not result.yara_reclassified


def test_build_indicator_sets_yara_reclassified_flag():
    obj, result = build_indicator("YARA", "d83494bd8a7f816ce39576c776e67c2e9f568080")
    assert result.yara_reclassified
    assert obj["x_otx_yara_reclassified"] is True
    assert obj["x_otx_indicator_type"] == "YARA"
    assert obj["pattern_type"] == "stix"


def test_campaign_without_threat_actor_has_no_attributed_to():
    mapper = StixMapper()
    pulse = {
        "pulse_id": "111111111111111111111111",
        "title": "Campaign Only",
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
        "targeted_countries": ["United States of America"],
        "references": [],
        "adversary": "",
        "campaign": "OperationX",
        "iocs": [],
    }
    mapper.map_pulse(pulse)
    attributed = [r for r in mapper.relationships if r.get("relationship_type") == "attributed-to"]
    targets = [r for r in mapper.relationships if r.get("relationship_type") == "targets"]
    assert attributed == []
    assert len(targets) == 1


def test_campaign_without_countries_has_no_targets():
    mapper = StixMapper()
    pulse = {
        "pulse_id": "222222222222222222222222",
        "title": "Campaign Actor",
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
    targets = [r for r in mapper.relationships if r.get("relationship_type") == "targets"]
    assert len(attributed) == 1
    assert targets == []


def test_invalid_reference_preserved_not_in_external_references():
    mapper = StixMapper()
    pulse = {
        "pulse_id": "333333333333333333333333",
        "title": "Bad Ref",
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
        "references": ["IOCs.rtf", "https://example.com/report"],
        "adversary": "",
        "campaign": "",
        "iocs": [],
    }
    report = mapper.map_pulse(pulse)
    urls = [ref["url"] for ref in report.get("external_references", [])]
    assert "IOCs.rtf" not in urls
    assert "https://example.com/report" in urls
    assert report["x_otx_invalid_references"] == ["IOCs.rtf"]
