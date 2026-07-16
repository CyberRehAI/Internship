from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.core.logging import configure_logging
from app.stix.converter import convert_jsonl_to_stix, convert_jsonl_to_stix_jsonl_bundles


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        prog="otx-to-stix",
        description="Convert AlienVault OTX pulse JSONL into a STIX 2.1 bundle.",
    )
    parser.add_argument("--input", default="data/otx_pulses.jsonl", help="Input JSONL file.")
    parser.add_argument("--output", default="data/otx_stix_bundle.json", help="Output STIX bundle (.json) or per-pulse bundles (.jsonl).")
    parser.add_argument("--stats", default="data/stix_conversion.stats.json", help="Conversion statistics JSON.")
    parser.add_argument("--errors", default="data/stix_conversion.errors.jsonl", help="Conversion errors JSONL.")
    parser.add_argument("--validate", action="store_true", help="Validate bundle with stix2-validator.")
    parser.add_argument(
        "--validate-debug",
        action="store_true",
        help="Report object IDs, types, and errors for failed validation.",
    )
    parser.add_argument("--strict", action="store_true", help="Treat validator warnings as failures.")
    parser.add_argument(
        "--preserve-source",
        action="store_true",
        help="Embed full original pulse JSON in each report as x_otx_source (larger bundle).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars (enabled automatically on interactive terminals).",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args(argv)
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    output_path = Path(args.output)
    convert_kwargs = {
        "stats_path": Path(args.stats),
        "errors_path": Path(args.errors),
        "validate": args.validate,
        "validate_debug": args.validate_debug,
        "strict": args.strict,
        "preserve_source": args.preserve_source,
        "show_progress": False if args.no_progress else None,
    }

    if output_path.suffix.lower() == ".jsonl":
        summary = convert_jsonl_to_stix_jsonl_bundles(
            Path(args.input),
            output_path,
            **convert_kwargs,
        )
    else:
        summary = convert_jsonl_to_stix(
            Path(args.input),
            output_path,
            **convert_kwargs,
        )
    logger.info("Summary: %s", summary)

    if args.validate and not summary.get("validation_ok", True):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
