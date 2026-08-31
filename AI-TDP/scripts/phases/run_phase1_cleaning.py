"""
Phase 1 — clean SWaT.A12 multilayer 1s CSV.

Usage (from AI-TDP root):
  python scripts/phases/run_phase1_cleaning.py
  python scripts/phases/run_phase1_cleaning.py --input data/swat/multilayer/swat_multilayer_1s.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from behavior.data.cleaning import clean_swat_multilayer, report_to_markdown

DEFAULT_INPUT = ROOT / "data" / "swat" / "multilayer" / "swat_multilayer_1s.csv"
DEFAULT_OUTPUT = ROOT / "data" / "swat" / "multilayer" / "swat_multilayer_1s_clean.csv"
DEFAULT_SCHEMA = ROOT / "behavior" / "outputs" / "feature_schema.json"
DEFAULT_REPORT_MD = ROOT / "reports" / "swat" / "swat_cleaning_report.md"
DEFAULT_REPORT_JSON = ROOT / "reports" / "swat" / "swat_cleaning_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1: clean SWaT multilayer CSV")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    print(f"Loading {args.input} ...")
    df = pd.read_csv(args.input, low_memory=False)
    clean, report = clean_swat_multilayer(df)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.schema.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)

    # Persist timestamp as string for CSV readability
    out = clean.copy()
    out["t_stamp"] = out["t_stamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_csv(args.output, index=False)
    print(f"Wrote cleaned CSV: {args.output}  shape={clean.shape}")

    schema = {
        "source": str(args.input).replace("\\", "/"),
        "cleaned": str(args.output).replace("\\", "/"),
        "n_rows": report["n_rows_out"],
        "n_cols": report["n_cols_out"],
        "feature_counts": report["feature_counts"],
        "column_groups": report["column_groups"],
        "dropped_columns": report["dropped_columns"],
    }
    args.schema.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote schema: {args.schema}")

    # JSON report: drop huge column lists duplication if needed — keep full for reproducibility
    args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.report_md.write_text(report_to_markdown(report), encoding="utf-8")
    print(f"Wrote report: {args.report_md}")
    print(f"Wrote report JSON: {args.report_json}")

    fc = report["feature_counts"]
    print(
        "Summary: "
        f"phys={fc['physical']} protocol={fc['protocol_total']} "
        f"net={fc['network']} features={fc['features_total']} "
        f"dropped_alarms={len(report['dropped_columns'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
