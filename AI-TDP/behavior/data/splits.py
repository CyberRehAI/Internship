"""Locked time splits for SWaT.A12 behavior pipeline (README §6.1)."""

from __future__ import annotations

from typing import List, Literal, Optional, Union

import pandas as pd

TIMESTAMP_COL = "t_stamp"
DAY_START = pd.Timestamp("2026-03-11 09:00:00")
TRAIN_END = pd.Timestamp("2026-03-11 12:00:00")
ATTACK_START = pd.Timestamp("2026-03-11 13:00:00")
DAY_END = pd.Timestamp("2026-03-11 17:00:59")

SplitName = Literal["train", "val", "test"]


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[TIMESTAMP_COL] = pd.to_datetime(out[TIMESTAMP_COL], errors="raise")
    return out


def train_mask(timestamps: pd.Series) -> pd.Series:
    """Seconds used to fit scalers / train encoders: t < 12:00."""
    return timestamps < TRAIN_END


def split_from_window(
    start_ts: Union[pd.Timestamp, str],
    end_ts: Union[pd.Timestamp, str],
) -> Optional[SplitName]:
    """
    Assign split only if the window is fully contained in one period.

    Train:  start,end in [09:00:00, 12:00:00)
    Val:    start,end in [12:00:00, 13:00:00)
    Test:   start,end in [13:00:00, 17:00:59]
    Otherwise return None (boundary-straddling window — discard).
    """
    start = pd.Timestamp(start_ts)
    end = pd.Timestamp(end_ts)
    if start > end:
        return None
    if start >= DAY_START and end < TRAIN_END:
        return "train"
    if start >= TRAIN_END and end < ATTACK_START:
        return "val"
    if start >= ATTACK_START and end <= DAY_END:
        return "test"
    return None


def label_from_split(split: SplitName) -> int:
    """Coarse attack-period label: 1 for test, else 0."""
    return 1 if split == "test" else 0


def verify_window_splits(
    start_times: List[str],
    end_times: List[str],
    splits: List[str],
) -> dict:
    """Return leakage checks for full-containment split assignment."""
    checks = {
        "train_ok": True,
        "val_ok": True,
        "test_ok": True,
        "violations": [],
    }
    for start_s, end_s, split in zip(start_times, end_times, splits):
        start = pd.Timestamp(start_s)
        end = pd.Timestamp(end_s)
        expected = split_from_window(start, end)
        if expected is None or expected != split:
            checks["violations"].append(
                {
                    "start": start_s,
                    "end": end_s,
                    "split": split,
                    "expected": expected,
                }
            )
        if split == "train" and not (start >= DAY_START and end < TRAIN_END):
            checks["train_ok"] = False
        if split == "val" and not (start >= TRAIN_END and end < ATTACK_START):
            checks["val_ok"] = False
        if split == "test" and not (start >= ATTACK_START and end <= DAY_END):
            checks["test_ok"] = False
    checks["all_ok"] = (
        checks["train_ok"]
        and checks["val_ok"]
        and checks["test_ok"]
        and not checks["violations"]
    )
    return checks
