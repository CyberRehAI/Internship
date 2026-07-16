from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from app.stix.exporter import assemble_bundle, export_bundle
from app.stix.mapper import StixMapper
from app.stix.parser import iter_pulses
from app.stix.progress import count_jsonl_records, log_phase, track
from app.stix.stats import write_errors, write_stats
from app.stix.types import ConversionError, ConversionStats
from app.stix.validator import validate_bundle

logger = logging.getLogger(__name__)


def convert_jsonl_to_stix(
    input_path: Path,
    output_path: Path,
    *,
    stats_path: Path | None = None,
    errors_path: Path | None = None,
    validate: bool = False,
    validate_debug: bool = False,
    strict: bool = False,
    preserve_source: bool = False,
    show_progress: bool | None = None,
) -> dict:
    mapper = StixMapper(preserve_source=preserve_source)
    pulse_total = count_jsonl_records(input_path)
    log_phase(f"Converting {pulse_total} pulses from {input_path.name}...", enabled=show_progress)

    for pulse in track(
        iter_pulses(input_path),
        total=pulse_total,
        desc="Converting pulses",
        unit="pulse",
        enabled=show_progress,
    ):
        try:
            mapper.map_pulse(pulse)
        except Exception as exc:
            pulse_id = str(pulse.get("pulse_id") or "")
            mapper._record_error(pulse_id, None, "pulse_map", str(exc))
            logger.exception("Failed to map pulse %s", pulse_id)

    log_phase("Assembling STIX bundle...", enabled=show_progress)
    bundle = assemble_bundle(mapper.registry.all_objects(), mapper.relationships, mapper.used_tlp)
    bundle["id"] = f"bundle--{uuid.uuid4()}"
    log_phase(f"Writing bundle to {output_path.name}...", enabled=show_progress)
    export_bundle(bundle, output_path)

    output_bytes = output_path.stat().st_size if output_path.exists() else 0
    if stats_path:
        write_stats(mapper.stats, stats_path, output_bytes=output_bytes)
    if errors_path:
        write_errors(mapper.errors, errors_path)

    validation_ok = True
    validation_messages: list[str] = []
    if validate:
        validation_ok, validation_messages = validate_bundle(
            bundle,
            strict=strict,
            debug=validate_debug,
            show_progress=show_progress,
        )
        for msg in validation_messages:
            if msg.startswith("warning:"):
                logger.warning(msg)
            else:
                logger.error(msg)

    summary = mapper.stats.to_dict()
    summary["output_path"] = str(output_path)
    summary["output_bytes"] = output_bytes
    summary["validation_ok"] = validation_ok
    summary["validation_messages"] = validation_messages
    logger.info(
        "Conversion complete: pulses=%s iocs=%s objects=%s relationships=%s bytes=%s",
        summary["pulses_processed"],
        summary["iocs_processed"],
        summary["total_objects"],
        summary["relationships"],
        output_bytes,
    )
    return summary


def convert_jsonl_to_stix_jsonl_bundles(
    input_path: Path,
    output_path: Path,
    *,
    stats_path: Path | None = None,
    errors_path: Path | None = None,
    validate: bool = False,
    validate_debug: bool = False,
    strict: bool = False,
    preserve_source: bool = False,
    show_progress: bool | None = None,
) -> dict:
    aggregate_stats = ConversionStats()
    all_errors: list[ConversionError] = []
    pulse_total = count_jsonl_records(input_path)
    log_phase(
        f"Converting {pulse_total} pulses to per-pulse bundles from {input_path.name}...",
        enabled=show_progress,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    validation_ok = True
    validation_messages: list[str] = []

    with output_path.open("w", encoding="utf-8", newline="\n") as out_handle:
        for pulse in track(
            iter_pulses(input_path),
            total=pulse_total,
            desc="Converting pulses",
            unit="pulse",
            enabled=show_progress,
        ):
            mapper = StixMapper(preserve_source=preserve_source)
            try:
                mapper.map_pulse(pulse)
            except Exception as exc:
                pulse_id = str(pulse.get("pulse_id") or "")
                mapper._record_error(pulse_id, None, "pulse_map", str(exc))
                logger.exception("Failed to map pulse %s", pulse_id)

            bundle = assemble_bundle(
                mapper.registry.all_objects(),
                mapper.relationships,
                mapper.used_tlp,
            )
            bundle["id"] = f"bundle--{uuid.uuid4()}"

            if validate:
                bundle_ok, bundle_messages = validate_bundle(
                    bundle,
                    strict=strict,
                    debug=validate_debug,
                    show_progress=False,
                )
                if not bundle_ok:
                    validation_ok = False
                validation_messages.extend(bundle_messages)
                for msg in bundle_messages:
                    if msg.startswith("warning:"):
                        logger.warning(msg)
                    else:
                        logger.error(msg)

            out_handle.write(json.dumps(bundle, separators=(",", ":"), ensure_ascii=False))
            out_handle.write("\n")

            aggregate_stats.merge_from(mapper.stats)
            all_errors.extend(mapper.errors)

    output_bytes = output_path.stat().st_size if output_path.exists() else 0
    if stats_path:
        write_stats(aggregate_stats, stats_path, output_bytes=output_bytes)
    if errors_path:
        write_errors(all_errors, errors_path)

    summary = aggregate_stats.to_dict()
    summary["output_path"] = str(output_path)
    summary["output_bytes"] = output_bytes
    summary["output_format"] = "bundle-jsonl"
    summary["bundles_written"] = aggregate_stats.pulses_processed
    summary["validation_ok"] = validation_ok
    summary["validation_messages"] = validation_messages
    logger.info(
        "Conversion complete: pulses=%s bundles=%s iocs=%s objects=%s relationships=%s bytes=%s",
        summary["pulses_processed"],
        summary["bundles_written"],
        summary["iocs_processed"],
        summary["total_objects"],
        summary["relationships"],
        output_bytes,
    )
    return summary
