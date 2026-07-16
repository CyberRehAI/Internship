# OTX Pulse JSONL → STIX 2.1 Converter

Convert crawler output (`data/otx_pulses.jsonl`) into STIX 2.1 bundles suitable for OpenCTI and other TAXII-compatible platforms.

## Quick start

**Single combined bundle (default):**

```bash
cd backend
python -m pip install -r requirements.txt
python -m app.cli.otx_to_stix --input data/otx_pulses.jsonl --output data/otx_stix_bundle.json --validate
```

**One STIX bundle per pulse (JSONL output):**

```bash
python -m app.cli.otx_to_stix --input data/all_otx_pulses.jsonl --output data/otx_stix_bundles.jsonl
```

Use a `.jsonl` output path to emit one self-contained STIX 2.1 bundle per input pulse (one bundle per line). Validation is off by default for this mode; add `--validate` to validate each bundle.

Add `--preserve-source` when you need the full original pulse embedded in each report (increases bundle size).

## Outputs

| File | Description |
|---|---|
| `data/otx_stix_bundle.json` | Single STIX 2.1 bundle (all SDOs + relationships + TLP markings) |
| `data/otx_stix_bundles.jsonl` | One STIX 2.1 bundle per pulse (JSONL; each line is a complete bundle) |
| `data/stix_conversion.stats.json` | Conversion statistics (includes `relationships_by_type`) |
| `data/stix_conversion.errors.jsonl` | Per-pulse/per-IOC errors |

## Mapping summary

| OTX field | STIX object |
|---|---|
| Each pulse | `report` |
| `author` | `identity` |
| `adversary`, `threat_actors[]` | `threat-actor` |
| `campaign` | `campaign` |
| `malware_families[]` | `malware` |
| `attack_ids[]` | `attack-pattern` |
| `targeted_countries[]` | `location` |
| `references`, pulse URL | `external_references` on report |
| `tags`, `industries` | `labels` / `x_otx_industries` |
| `tlp` | TLP `marking-definition` via `object_marking_refs` |
| Each IOC | `indicator` (+ `vulnerability` for CVE) |

Unmapped or exotic fields are preserved on objects as `x_otx_*` properties. Use `--preserve-source` to embed the full original pulse in each report as `x_otx_source`.

## Relationships

Reports link to related SDOs via `object_refs` only (no `report → related-to` SROs).

- `indicator` → `indicates` → `malware`
- `threat-actor` → `uses` → `malware`
- `campaign` → `attributed-to` → `threat-actor` (only when pulse has both `campaign` and `adversary`/`threat_actors`)
- `malware` → `uses` → `attack-pattern`
- `campaign` → `targets` → `location` (only when pulse has both `campaign` and `targeted_countries`)

Campaign relationships are never inferred from title, description, or tags. The pulse JSONL `campaign` field must be populated.

## YARA IOC handling

OTX sometimes labels IOCs as `YARA` when the value is actually a file hash. The converter:

- Keeps `pattern_type: "yara"` only when the value looks like a real YARA rule (`rule`, `strings:`, `condition:`)
- Reclassifies hex hashes to STIX file-hash patterns (`pattern_type: "stix"`)
- Preserves the original OTX type in `x_otx_indicator_type` and value in `x_otx_original_value`
- Sets `x_otx_yara_reclassified: true` when a YARA-typed IOC was mapped to STIX instead

## Invalid references

Report `references[]` values must be valid URIs (`http`, `https`, or `ftp`) to appear in `external_references`. Invalid values are preserved on the report as `x_otx_invalid_references`.

## Deterministic IDs

All STIX IDs use UUIDv5 with a fixed namespace so repeated conversions produce identical IDs for the same entities.

## Validation

Use `--validate` to run `stix2` parsing and per-object `stix2-validator` checks. Add
`--validate-debug` to report the object type, ID, and validation error for failed
objects.

The converter pins `stix2-validator==3.2.0`. Releases 3.3.0 and 3.3.1 omit the
bundled STIX JSON schemas and cannot validate STIX 2.1 content.

Add `--strict` to treat best-practice warnings as failures. Strict mode may reject
the converter's intentional deterministic UUIDv5 IDs and `x_otx_*` custom properties;
default validation permits these warnings.

Progress bars are shown automatically in interactive terminals for pulse conversion
and per-object validation. Use `--no-progress` to disable them.

## OpenCTI import notes

- Import the single bundle JSON via OpenCTI import workflow, or import per-pulse bundles from JSONL one line at a time.
- TLP marking definitions are included in each bundle.
- Large bundles may take time to import; monitor object counts in `stix_conversion.stats.json`.

## Known limitations

- STIX has no native Industry SDO; industries are stored as report labels and `x_otx_industries`.
- Exotic OTX IOC types use best-effort STIX patterns with full original values in `x_otx_*` fields.
- Windows Defender may flag output files containing malicious IOC strings (same as the JSONL source).

## Tests

```bash
cd backend
python -m pytest tests/stix -q
```
