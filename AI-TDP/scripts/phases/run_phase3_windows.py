"""
Phase 3 — windows, scaling, validation split.

Usage (from AI-TDP root):
  python scripts/phases/run_phase3_windows.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from behavior.data.dataset import make_loader
from behavior.data.scaling import fit_transform_domains, save_scalers
from behavior.data.splits import TIMESTAMP_COL, TRAIN_END, ensure_datetime, train_mask
from behavior.data.windows import DEFAULT_STRIDE, DEFAULT_T, build_windows, partition_and_save

DEFAULT_INPUT = ROOT / "data" / "swat" / "multilayer" / "swat_multilayer_1s_selected.csv"
DEFAULT_SCHEMA = ROOT / "behavior" / "outputs" / "feature_schema_selected.json"
DEFAULT_CONFIG = ROOT / "behavior" / "outputs" / "config_windows.json"
DEFAULT_SCALERS = ROOT / "behavior" / "outputs" / "scalers"
DEFAULT_WINDOWS = ROOT / "behavior" / "outputs" / "windows"
DEFAULT_REPORT = ROOT / "reports" / "swat" / "swat_phase3_windows_summary.md"


def write_summary_md(path: Path, config: dict, checks: dict, smoke: dict) -> None:
    counts = config["split_counts"]
    dims = config["feature_dims"]
    lines = [
        "# SWaT.A12 Phase 3 — Windows & Scaling Summary",
        "",
        "**Phase:** 3 — Windows, scaling, validation split",
        "",
        "## Config",
        "",
        f"| Item | Value |",
        f"| :--- | :--- |",
        f"| T / stride | {config['T']} / {config['stride']} |",
        f"| log1p writes | {config['log1p_writes']} |",
        f"| Scaler | {config['scaler_type']} (fit on Train seconds) |",
        f"| n_fit_rows | {config['n_fit_rows']} |",
        f"| Physical dim | {dims['physical']} |",
        f"| Protocol dim | {dims['protocol']} |",
        f"| Network dim | {dims['network']} |",
        "",
        "## Window counts",
        "",
        f"| Split | N windows | start_time min | end_time max |",
        f"| :--- | ---: | :--- | :--- |",
    ]
    for split in ("train", "val", "test"):
        b = config["bounds"][split]
        lines.append(
            f"| {split} | {b['n']} | {b['start_time_min']} | {b['end_time_max']} |"
        )
    lines.extend(
        [
            "",
            f"**Total windows kept:** {sum(counts.values())}",
            f"**Candidates / discarded (boundary):** {checks.get('n_candidates')} / {checks.get('n_discarded_boundary')}",
            "",
            "## Split rule",
            "",
            "- Windows must be fully contained in Train / Val / Test (start **and** end).",
            "- Boundary-straddling windows are discarded.",
            "",
            "## Leakage checks",
            "",
            f"- Train fully in [09:00, 12:00): **{checks['train_ok']}**",
            f"- Val fully in [12:00, 13:00): **{checks['val_ok']}**",
            f"- Test fully in [13:00, 17:00:59]: **{checks['test_ok']}**",
            f"- All OK: **{checks['all_ok']}**",
            "",
            "## DataLoader smoke test",
            "",
            f"- batch net shape: `{smoke['net_shape']}`",
            f"- batch proto shape: `{smoke['proto_shape']}`",
            f"- batch phys shape: `{smoke['phys_shape']}`",
            "",
            "## Artifacts",
            "",
        ]
    )
    for k, v in config["artifacts"].items():
        lines.append(f"- **{k}:** `{v}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: scale + window SWaT selected CSV")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--scalers-dir", type=Path, default=DEFAULT_SCALERS)
    parser.add_argument("--windows-dir", type=Path, default=DEFAULT_WINDOWS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--T", type=int, default=DEFAULT_T)
    parser.add_argument("--stride", type=int, default=DEFAULT_STRIDE)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1
    if not args.schema.is_file():
        print(f"ERROR: schema not found: {args.schema}", file=sys.stderr)
        return 1

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    groups = schema["column_groups"]
    physical_cols = list(groups["physical"])
    write_cols = list(groups["writes"])
    last_cols = list(groups["last_value"])
    network_cols = list(groups["network"])
    protocol_cols = write_cols + last_cols

    print(f"Loading {args.input} ...")
    df = ensure_datetime(pd.read_csv(args.input, low_memory=False))
    fit_rows = int(train_mask(df[TIMESTAMP_COL]).sum())
    print(f"Train seconds for scaler fit: {fit_rows} (t < {TRAIN_END})")

    print("log1p writes + RobustScaler (Train-only fit) ...")
    scaled, scalers, scale_info = fit_transform_domains(
        df, physical_cols, write_cols, last_cols, network_cols
    )
    if scale_info["n_fit_rows"] != fit_rows:
        raise AssertionError(
            f"n_fit_rows mismatch: {scale_info['n_fit_rows']} vs {fit_rows}"
        )
    scaler_paths = save_scalers(scalers, args.scalers_dir)
    print(f"Wrote scalers to {args.scalers_dir}")

    print(f"Building windows T={args.T} stride={args.stride} ...")
    arrays, meta_rows, checks = build_windows(
        scaled,
        physical_cols=physical_cols,
        protocol_cols=protocol_cols,
        network_cols=network_cols,
        T=args.T,
        stride=args.stride,
    )
    if not checks["all_ok"]:
        print(f"ERROR: leakage checks failed: {checks}", file=sys.stderr)
        return 1

    part = partition_and_save(arrays, meta_rows, args.windows_dir)
    print(f"Split counts: {part['counts']}")

    # Smoke-test DataLoader
    loader = make_loader(
        args.windows_dir, "train", batch_size=args.batch_size, shuffle=False, meta_rows=meta_rows
    )
    batch = next(iter(loader))
    smoke = {
        "net_shape": list(batch["net"].shape),
        "proto_shape": list(batch["proto"].shape),
        "phys_shape": list(batch["phys"].shape),
    }
    assert batch["net"].shape[1:] == (args.T, len(network_cols))
    assert batch["proto"].shape[1:] == (args.T, len(protocol_cols))
    assert batch["phys"].shape[1:] == (args.T, len(physical_cols))
    print(f"DataLoader smoke OK: {smoke}")

    config = {
        "input": str(args.input).replace("\\", "/"),
        "schema": str(args.schema).replace("\\", "/"),
        "T": args.T,
        "stride": args.stride,
        "log1p_writes": True,
        "scaler_type": "RobustScaler",
        "n_fit_rows": scale_info["n_fit_rows"],
        "feature_dims": {
            "physical": len(physical_cols),
            "protocol": len(protocol_cols),
            "network": len(network_cols),
        },
        "column_groups": {
            "physical": physical_cols,
            "writes": write_cols,
            "last_value": last_cols,
            "protocol": protocol_cols,
            "network": network_cols,
        },
        "split_rule": "fully_contained_start_and_end",
        "label_rule": "1 if split == test else 0",
        "split_counts": part["counts"],
        "bounds": part["bounds"],
        "n_candidates": checks.get("n_candidates"),
        "n_discarded_boundary": checks.get("n_discarded_boundary"),
        "leakage_checks": checks,
        "artifacts": {
            "config": str(args.config).replace("\\", "/"),
            "scalers": scaler_paths,
            "windows": part["paths"],
            "report": str(args.report).replace("\\", "/"),
        },
        "dataloader_smoke": smoke,
    }
    args.config.parent.mkdir(parents=True, exist_ok=True)
    args.config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Wrote {args.config}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_summary_md(args.report, config, checks, smoke)
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
