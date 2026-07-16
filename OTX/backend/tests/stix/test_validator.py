import json
from pathlib import Path

from app.stix.converter import convert_jsonl_to_stix
from app.stix.validator import _ensure_schemas_available, validate_bundle


def _convert_minimal_bundle(tmp_path: Path) -> dict:
    pulse = {
        "pulse_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Validation Test",
        "description": "Minimal validation fixture",
        "author": "AlienVault",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "tlp": "white",
        "tags": [],
        "malware_families": ["TestMalware"],
        "attack_ids": [],
        "threat_actors": [],
        "industries": [],
        "targeted_countries": [],
        "references": [],
        "adversary": "",
        "campaign": "",
        "iocs": [
            {
                "indicator": "evil.example",
                "type": "domain",
                "role": "",
                "description": "",
            }
        ],
    }
    input_path = tmp_path / "sample.jsonl"
    output_path = tmp_path / "bundle.json"
    input_path.write_text(json.dumps(pulse) + "\n", encoding="utf-8")
    convert_jsonl_to_stix(input_path, output_path)
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_stix_21_schemas_are_available():
    assert _ensure_schemas_available("2.1") is None


def test_validate_bundle_minimal_converter_output_passes(tmp_path: Path):
    bundle = _convert_minimal_bundle(tmp_path)

    is_valid, messages = validate_bundle(bundle)

    assert is_valid
    assert messages == []


def test_report_with_invalid_reference_passes_validation(tmp_path: Path):
    pulse = {
        "pulse_id": "bbbbbbbbbbbbbbbbbbbbbbbb",
        "title": "Invalid Ref Test",
        "description": "Minimal validation fixture",
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
        "references": ["IOCs.rtf"],
        "adversary": "",
        "campaign": "",
        "iocs": [],
    }
    input_path = tmp_path / "invalid_ref.jsonl"
    output_path = tmp_path / "bundle.json"
    input_path.write_text(json.dumps(pulse) + "\n", encoding="utf-8")
    summary = convert_jsonl_to_stix(input_path, output_path, validate=True)
    assert summary["validation_ok"] is True
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    report = next(obj for obj in bundle["objects"] if obj["type"] == "report")
    assert report["x_otx_invalid_references"] == ["IOCs.rtf"]


def test_validate_debug_reports_object_details(tmp_path: Path):
    bundle = _convert_minimal_bundle(tmp_path)
    report = next(obj for obj in bundle["objects"] if obj["type"] == "report")
    report["x_otx_invalid_empty_array"] = []

    is_valid, messages = validate_bundle(bundle, debug=True)

    assert not is_valid
    assert any(report["id"] in message and "report" in message for message in messages)
    assert any("empty arrays are not allowed" in message for message in messages)
    assert messages[-1] == "Validation debug summary: 1 invalid object(s)."
