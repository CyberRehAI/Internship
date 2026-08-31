"""
Merge SWaT.A12 physical historian + CIP writes + network 1s summaries.

CIP symbolic tags are independent control features (no historian mapping).

PCAP timestamps from tshark are Unix epoch (UTC). The SWaT historian uses
local plant wall-clock (Singapore, UTC+8). Epochs are converted to Asia/Singapore
naive datetimes before joining.

Usage:
  python scripts/dataset/build_swat_multilayer_dataset.py
  python scripts/dataset/build_swat_multilayer_dataset.py --tz Asia/Singapore
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_multilayer_common import (
    CIP_WRITES_CSV,
    HISTORIAN_CSV,
    MULTILAYER_CSV,
    MULTILAYER_SUMMARY,
    NETWORK_1S_CSV,
    TAG_COLUMNS_CSV,
    ensure_out_dirs,
    sanitize_tag_column,
)


def epoch_to_local_index(seconds, tz: str) -> pd.DatetimeIndex:
    """Unix epoch seconds (UTC) -> naive local wall-clock matching historian."""
    dt = pd.to_datetime(pd.Series(seconds), unit="s", utc=True)
    dt = dt.dt.tz_convert(tz).dt.tz_localize(None)
    return pd.DatetimeIndex(dt)


def _pivot_cip_writes(writes: pd.DataFrame, max_tags: int | None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (pivoted per-second features, tag<->column map)."""
    if writes.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["tag_name", "col_writes", "col_last_value", "n_writes"])

    w = writes.copy()
    w["frame.time_epoch"] = pd.to_numeric(w["frame.time_epoch"], errors="coerce")
    w = w.dropna(subset=["frame.time_epoch"])
    w["second"] = w["frame.time_epoch"].astype(float).astype(int)
    w["tag_name"] = w["tag_name"].fillna("").astype(str).str.strip()
    w = w[w["tag_name"] != ""]
    w["data_int"] = pd.to_numeric(w["data_int"], errors="coerce")

    tag_counts = w["tag_name"].value_counts()
    if max_tags is not None and len(tag_counts) > max_tags:
        keep = set(tag_counts.head(max_tags).index)
        w = w[w["tag_name"].isin(keep)]
        tag_counts = w["tag_name"].value_counts()

    map_rows = []
    used: Dict[str, str] = {}
    for tag, n in tag_counts.items():
        base = sanitize_tag_column(tag)
        suffix = base
        i = 2
        while suffix in used.values():
            suffix = f"{base}_{i}"
            i += 1
        used[tag] = suffix
        map_rows.append(
            {
                "tag_name": tag,
                "col_writes": f"writes_{suffix}",
                "col_last_value": f"last_value_{suffix}",
                "n_writes": int(n),
            }
        )
    tag_map = pd.DataFrame(map_rows)
    w["col_key"] = w["tag_name"].map(used)

    grouped = (
        w.sort_values("frame.time_epoch")
        .groupby(["second", "col_key"], as_index=False)
        .agg(write_count=("tag_name", "size"), last_value=("data_int", "last"))
    )

    counts = grouped.pivot(index="second", columns="col_key", values="write_count")
    values = grouped.pivot(index="second", columns="col_key", values="last_value")
    counts = counts.rename(columns=lambda c: f"writes_{c}")
    values = values.rename(columns=lambda c: f"last_value_{c}")
    pivoted = counts.join(values, how="outer").sort_index()
    write_cols = [c for c in pivoted.columns if c.startswith("writes_")]
    pivoted[write_cols] = pivoted[write_cols].fillna(0).astype(int)
    return pivoted, tag_map


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SWaT multi-layer 1s dataset")
    parser.add_argument(
        "--max-tags",
        type=int,
        default=None,
        help="Keep only top-N CIP tags by write count (default: all)",
    )
    parser.add_argument(
        "--historian",
        type=Path,
        default=HISTORIAN_CSV,
        help="Path to historian CSV",
    )
    parser.add_argument(
        "--tz",
        default="Asia/Singapore",
        help="IANA timezone for PCAP epoch -> historian wall-clock (default: Asia/Singapore)",
    )
    args = parser.parse_args()
    ensure_out_dirs()

    if not args.historian.is_file():
        raise FileNotFoundError(args.historian)

    print(f"Loading historian: {args.historian}")
    phys = pd.read_csv(args.historian, low_memory=False)
    if "t_stamp" not in phys.columns:
        raise ValueError("historian missing t_stamp column")
    phys["t_stamp"] = pd.to_datetime(phys["t_stamp"], errors="coerce")
    phys = phys.dropna(subset=["t_stamp"]).sort_values("t_stamp")
    phys = phys.set_index("t_stamp")
    phys.index = phys.index.floor("s")
    phys = phys[~phys.index.duplicated(keep="last")]

    print(f"Loading CIP writes: {CIP_WRITES_CSV}")
    if CIP_WRITES_CSV.is_file():
        writes = pd.read_csv(CIP_WRITES_CSV)
    else:
        print("WARNING: cip_writes.csv missing - control layer empty")
        writes = pd.DataFrame()

    pivoted, tag_map = _pivot_cip_writes(writes, args.max_tags)
    if not tag_map.empty:
        tag_map.to_csv(TAG_COLUMNS_CSV, index=False)
        print(f"Tag column map: {TAG_COLUMNS_CSV} ({len(tag_map)} tags)")

    if not pivoted.empty:
        ctrl = pivoted.copy()
        ctrl.index = epoch_to_local_index(ctrl.index, args.tz)
        ctrl.index.name = "t_stamp"
        ctrl = ctrl[~ctrl.index.duplicated(keep="last")]
    else:
        ctrl = pd.DataFrame()

    print(f"Loading network 1s: {NETWORK_1S_CSV} (tz={args.tz})")
    if NETWORK_1S_CSV.is_file():
        net = pd.read_csv(NETWORK_1S_CSV)
        net_idx = epoch_to_local_index(net["timestamp"], args.tz)
        net = net.drop(columns=["timestamp"])
        net.index = net_idx
        net.index.name = "t_stamp"
        net = net[~net.index.duplicated(keep="last")].sort_index()
        net = net.rename(columns=lambda c: c if c.startswith("net_") else f"net_{c}")
    else:
        print("WARNING: network_1s.csv missing - network layer empty")
        net = pd.DataFrame()

    merged = phys.copy()
    write_cols: List[str] = []
    if not ctrl.empty:
        merged = merged.join(ctrl, how="left")
        write_cols = [c for c in merged.columns if c.startswith("writes_")]
        seconds_with_write = int((merged[write_cols].fillna(0).sum(axis=1) > 0).sum()) if write_cols else 0
        merged[write_cols] = merged[write_cols].fillna(0).astype(int)
    else:
        seconds_with_write = 0

    if not net.empty:
        merged = merged.join(net, how="left")
        net_fill = [c for c in merged.columns if c.startswith("net_")]
        seconds_with_network = (
            int((merged["net_total_pkts"].fillna(0) > 0).sum()) if "net_total_pkts" in merged.columns else 0
        )
        merged[net_fill] = merged[net_fill].fillna(0)
    else:
        seconds_with_network = 0

    phys_start, phys_end = merged.index.min(), merged.index.max()

    merged = merged.reset_index()
    merged.to_csv(MULTILAYER_CSV, index=False)

    summary = {
        "n_rows": int(len(merged)),
        "n_cols": int(merged.shape[1]),
        "phys_start": str(phys_start),
        "phys_end": str(phys_end),
        "pcap_timezone": args.tz,
        "n_cip_tag_features": int(len(tag_map)),
        "seconds_with_any_write": seconds_with_write,
        "seconds_with_network": seconds_with_network,
        "output": str(MULTILAYER_CSV.as_posix()),
        "columns_sample": list(merged.columns[:40]),
    }
    MULTILAYER_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {MULTILAYER_CSV} shape={merged.shape}")
    print(f"  seconds_with_any_write={seconds_with_write}, seconds_with_network={seconds_with_network}")
    print(f"Summary: {MULTILAYER_SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
