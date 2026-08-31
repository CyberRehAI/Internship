"""Sliding-window builders and NPZ persistence (Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from behavior.data.splits import (
    TIMESTAMP_COL,
    label_from_split,
    split_from_window,
    verify_window_splits,
)

DEFAULT_T = 60
DEFAULT_STRIDE = 10


def build_window_starts(n_rows: int, T: int = DEFAULT_T, stride: int = DEFAULT_STRIDE) -> List[int]:
    starts = []
    k = 0
    while k * stride + T <= n_rows:
        starts.append(k * stride)
        k += 1
    return starts


def build_windows(
    df: pd.DataFrame,
    physical_cols: Sequence[str],
    protocol_cols: Sequence[str],
    network_cols: Sequence[str],
    T: int = DEFAULT_T,
    stride: int = DEFAULT_STRIDE,
) -> Tuple[Dict[str, np.ndarray], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Build domain window tensors fully contained in Train/Val/Test.

    Boundary-straddling windows (start and end in different periods) are discarded.
    """
    n = len(df)
    starts = build_window_starts(n, T=T, stride=stride)
    timestamps = df[TIMESTAMP_COL].to_numpy()

    phys = df[list(physical_cols)].to_numpy(dtype=np.float32)
    proto = df[list(protocol_cols)].to_numpy(dtype=np.float32)
    net = df[list(network_cols)].to_numpy(dtype=np.float32)

    phys_list: List[np.ndarray] = []
    proto_list: List[np.ndarray] = []
    net_list: List[np.ndarray] = []
    labels_list: List[int] = []
    end_ordinal_list: List[int] = []

    meta_rows: List[Dict[str, Any]] = []
    start_times: List[str] = []
    end_times: List[str] = []
    splits: List[str] = []
    n_discarded = 0

    kept_index = 0
    for start in starts:
        end_idx = start + T - 1
        start_ts = pd.Timestamp(timestamps[start])
        end_ts = pd.Timestamp(timestamps[end_idx])
        split = split_from_window(start_ts, end_ts)
        if split is None:
            n_discarded += 1
            continue

        label = label_from_split(split)
        phys_list.append(phys[start : start + T])
        proto_list.append(proto[start : start + T])
        net_list.append(net[start : start + T])
        labels_list.append(label)
        end_ordinal_list.append(int(end_ts.value))

        start_str = start_ts.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_ts.strftime("%Y-%m-%d %H:%M:%S")
        start_times.append(start_str)
        end_times.append(end_str)
        splits.append(split)
        meta_rows.append(
            {
                "index": kept_index,
                "start_row": start,
                "end_row": end_idx,
                "start_time": start_str,
                "end_time": end_str,
                "split": split,
                "label": label,
            }
        )
        kept_index += 1

    checks = verify_window_splits(start_times, end_times, splits)
    checks["n_candidates"] = len(starts)
    checks["n_kept"] = len(meta_rows)
    checks["n_discarded_boundary"] = n_discarded

    if not phys_list:
        raise RuntimeError("No windows kept after full-containment split filter")

    arrays = {
        "phys": np.stack(phys_list, axis=0),
        "proto": np.stack(proto_list, axis=0),
        "net": np.stack(net_list, axis=0),
        "label": np.asarray(labels_list, dtype=np.int64),
        "end_time_ordinal": np.asarray(end_ordinal_list, dtype=np.int64),
    }
    return arrays, meta_rows, checks


def partition_and_save(
    arrays: Dict[str, np.ndarray],
    meta_rows: List[Dict[str, Any]],
    out_dir: Path,
) -> Dict[str, Any]:
    """Write train/val/test npz + meta.json; return split counts and paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    splits = [m["split"] for m in meta_rows]
    counts = {s: splits.count(s) for s in ("train", "val", "test")}
    paths: Dict[str, str] = {}

    for split_name in ("train", "val", "test"):
        idx = [i for i, m in enumerate(meta_rows) if m["split"] == split_name]
        idx_arr = np.asarray(idx, dtype=np.int64)
        path = out_dir / f"{split_name}.npz"
        np.savez_compressed(
            path,
            net=arrays["net"][idx_arr],
            proto=arrays["proto"][idx_arr],
            phys=arrays["phys"][idx_arr],
            label=arrays["label"][idx_arr],
            end_time_ordinal=arrays["end_time_ordinal"][idx_arr],
            indices=idx_arr,
        )
        paths[split_name] = str(path).replace("\\", "/")

    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta_rows, indent=2), encoding="utf-8")
    paths["meta"] = str(meta_path).replace("\\", "/")

    bounds = {}
    for split_name in ("train", "val", "test"):
        rows = [m for m in meta_rows if m["split"] == split_name]
        bounds[split_name] = {
            "n": len(rows),
            "start_time_min": min((m["start_time"] for m in rows), default=None),
            "start_time_max": max((m["start_time"] for m in rows), default=None),
            "end_time_min": min((m["end_time"] for m in rows), default=None),
            "end_time_max": max((m["end_time"] for m in rows), default=None),
        }

    return {"counts": counts, "paths": paths, "bounds": bounds}
