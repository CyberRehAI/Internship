"""Debug script for STIX 2.1 validation issues."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stix2validator import ValidationOptions, validate_file, validate_instance

from app.stix.converter import convert_jsonl_to_stix
from app.stix.validator import validate_bundle


def test_minimal_manual():
    print("=== Minimal manual STIX 2.1 bundle ===")
    report = {
        "type": "report",
        "spec_version": "2.1",
        "id": "report--11111111-1111-1111-1111-111111111111",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "name": "Test Report",
        "published": "2025-01-01T00:00:00.000Z",
        "report_types": ["threat-report"],
        "object_refs": ["indicator--22222222-2222-2222-2222-222222222222"],
    }
    indicator = {
        "type": "indicator",
        "spec_version": "2.1",
        "id": "indicator--22222222-2222-2222-2222-222222222222",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "name": "evil.com",
        "pattern": "[domain-name:value = 'evil.com']",
        "pattern_type": "stix",
        "valid_from": "2025-01-01T00:00:00.000Z",
    }
    rel = {
        "type": "relationship",
        "spec_version": "2.1",
        "id": "relationship--33333333-3333-3333-3333-333333333333",
        "created": "2025-01-01T00:00:00.000Z",
        "modified": "2025-01-02T00:00:00.000Z",
        "relationship_type": "indicates",
        "source_ref": "indicator--22222222-2222-2222-2222-222222222222",
        "target_ref": "malware--44444444-4444-4444-4444-444444444444",
    }
    bundle = {
        "type": "bundle",
        "id": "bundle--55555555-5555-5555-5555-555555555555",
        "objects": [report, indicator, rel],
    }
    opts = ValidationOptions(version="2.1")

    for obj in bundle["objects"]:
        r = validate_instance(obj, opts)
        print(f"  {obj['type']}: valid={r.is_valid} errors={len(r.errors)} warnings={len(r.warnings)}")
        for e in r.errors[:3]:
            print(f"    ERR: {e.message if hasattr(e, 'message') else e}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(bundle, f)
        path = f.name
    r = validate_file(path, opts)
    print(f"  validate_file(bundle): valid={r.is_valid} errors={len(r.errors)}")
    for e in r.errors[:5]:
        print(f"    ERR: {e.message if hasattr(e, 'message') else e}")
    Path(path).unlink(missing_ok=True)

    ok, msgs = validate_bundle(bundle)
    print(f"  validate_bundle(): ok={ok} messages={len(msgs)}")
    for m in msgs[:5]:
        print(f"    {m}")


def test_minimal_from_converter(tmp_dir: Path):
    print("\n=== Minimal bundle from our converter ===")
    pulse = {
        "pulse_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Debug Pulse",
        "description": "test",
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
        "iocs": [{"indicator": "evil.com", "type": "domain", "role": "", "description": ""}],
    }
    input_path = tmp_dir / "sample.jsonl"
    output_path = tmp_dir / "bundle.json"
    input_path.write_text(json.dumps(pulse) + "\n", encoding="utf-8")
    convert_jsonl_to_stix(input_path, output_path, validate=False)
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    print(f"  objects: {len(bundle['objects'])}")
    ok, msgs = validate_bundle(bundle)
    print(f"  validate_bundle(): ok={ok} messages={len(msgs)}")
    for m in msgs[:10]:
        print(f"    {m}")


def test_full_bundle_first_failures(bundle_path: Path, limit: int = 10):
    print(f"\n=== Full bundle first failures ({bundle_path}) ===")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    opts = ValidationOptions(version="2.1")
    failures = []
    for obj in bundle.get("objects", []):
        if not isinstance(obj, dict) or obj.get("type") == "bundle":
            continue
        r = validate_instance(obj, opts)
        if not r.is_valid:
            failures.append((obj.get("type"), obj.get("id"), r.errors))
            if len(failures) >= limit:
                break
    print(f"  total objects: {len(bundle['objects'])}")
    print(f"  first {len(failures)} failures:")
    for obj_type, obj_id, errors in failures:
        print(f"  {obj_type} {obj_id}:")
        for e in errors[:3]:
            print(f"    {e.message if hasattr(e, 'message') else e}")


if __name__ == "__main__":
    import stix2
    import stix2validator

    print(f"stix2={stix2.__version__} stix2validator={stix2validator.__version__}")
    test_minimal_manual()
    test_minimal_from_converter(Path(tempfile.mkdtemp()))
    full = Path("data/otx_stix_bundle.json")
    if full.exists():
        test_full_bundle_first_failures(full)
