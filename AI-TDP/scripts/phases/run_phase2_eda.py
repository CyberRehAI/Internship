"""
Phase 2 — EDA on cleaned SWaT multilayer CSV.

Usage (from AI-TDP root):
  python scripts/phases/run_phase2_eda.py
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

from behavior.data.eda import (
    build_eda_payload,
    eda_payload_to_markdown,
    ensure_datetime,
    run_all_plots,
    write_sparsity,
)
from behavior.data.feature_selection import (
    apply_drops,
    build_selected_schema,
    classify_variance,
    feature_counts_from_groups,
    filter_column_groups,
)

DEFAULT_INPUT = ROOT / "data" / "swat" / "multilayer" / "swat_multilayer_1s_clean.csv"
DEFAULT_SCHEMA = ROOT / "behavior" / "outputs" / "feature_schema.json"
DEFAULT_SELECTED_CSV = ROOT / "data" / "swat" / "multilayer" / "swat_multilayer_1s_selected.csv"
DEFAULT_SELECTED_SCHEMA = ROOT / "behavior" / "outputs" / "feature_schema_selected.json"
DEFAULT_FIG_DIR = ROOT / "reports" / "swat" / "eda"
DEFAULT_REPORT_MD = ROOT / "reports" / "swat" / "swat_eda_summary.md"
DEFAULT_REPORT_JSON = ROOT / "reports" / "swat" / "swat_eda_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2: EDA + zero-variance feature selection")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--selected-csv", type=Path, default=DEFAULT_SELECTED_CSV)
    parser.add_argument("--selected-schema", type=Path, default=DEFAULT_SELECTED_SCHEMA)
    parser.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1
    if not args.schema.is_file():
        print(f"ERROR: schema not found: {args.schema}", file=sys.stderr)
        return 1

    print(f"Loading {args.input} ...")
    df = ensure_datetime(pd.read_csv(args.input, low_memory=False))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    groups = schema["column_groups"]
    feature_cols = (
        list(groups["physical"])
        + list(groups["writes"])
        + list(groups["last_value"])
        + list(groups["network"])
    )

    print("Computing variance (full-day vs Train) ...")
    variance, dropped, attack_active = classify_variance(df, feature_cols)
    counts_before = feature_counts_from_groups(groups)
    groups_after = filter_column_groups(groups, dropped)
    counts_after = feature_counts_from_groups(groups_after)

    print(f"Full-day zero-variance drops: {len(dropped)}")
    print(f"Train-silent / attack-active kept: {len(attack_active)}")

    print("Generating figures ...")
    fig_paths = run_all_plots(df, groups, args.fig_dir)
    sparsity = write_sparsity(df, groups["writes"])

    selected = apply_drops(df, dropped)
    # column order: t_stamp + remaining groups
    ordered = (
        [groups.get("timestamp", "t_stamp")]
        + groups_after["physical"]
        + groups_after["writes"]
        + groups_after["last_value"]
        + groups_after["network"]
    )
    selected = selected[ordered]

    args.selected_csv.parent.mkdir(parents=True, exist_ok=True)
    out_csv = selected.copy()
    out_csv["t_stamp"] = out_csv["t_stamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out_csv.to_csv(args.selected_csv, index=False)
    print(f"Wrote selected CSV: {args.selected_csv}  shape={selected.shape}")

    selected_schema = build_selected_schema(
        schema,
        groups_after,
        dropped,
        attack_active,
        str(args.selected_csv),
    )
    args.selected_schema.parent.mkdir(parents=True, exist_ok=True)
    args.selected_schema.write_text(json.dumps(selected_schema, indent=2), encoding="utf-8")
    print(f"Wrote selected schema: {args.selected_schema}")

    payload = build_eda_payload(
        variance=variance,
        sparsity=sparsity,
        figure_paths=fig_paths,
        dropped=dropped,
        attack_active=attack_active,
        feature_counts_before=counts_before,
        feature_counts_after=counts_after,
    )
    args.report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.report_md.write_text(eda_payload_to_markdown(payload), encoding="utf-8")
    print(f"Wrote {args.report_md}")
    print(f"Wrote {args.report_json}")
    print(
        "Summary: "
        f"features {counts_before['features_total']} -> {counts_after['features_total']} "
        f"(dropped {len(dropped)} full-day ZV)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
