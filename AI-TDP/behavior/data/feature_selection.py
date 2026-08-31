"""Apply Phase 2 feature selection (drop full-day zero-variance columns)."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from behavior.data.columns import TIMESTAMP_COL
from behavior.data.eda import VAR_EPS, compute_variance_table


def classify_variance(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Returns variance table, drop list (full-day constant), keep-attack-active list.
    """
    table = compute_variance_table(df, feature_cols)
    dropped = table.loc[table["full_day_constant"], "feature"].tolist()
    attack_active = table.loc[
        table["train_constant_attack_active"], "feature"
    ].tolist()
    return table, dropped, attack_active


def apply_drops(
    df: pd.DataFrame,
    drop_cols: Sequence[str],
) -> pd.DataFrame:
    cols = [c for c in drop_cols if c in df.columns]
    return df.drop(columns=cols)


def filter_column_groups(
    groups: Dict[str, Any],
    drop_cols: Sequence[str],
) -> Dict[str, Any]:
    drop_set = set(drop_cols)
    out: Dict[str, Any] = {"timestamp": groups.get("timestamp", TIMESTAMP_COL)}
    for key in ("physical", "writes", "last_value", "network"):
        cols = groups.get(key) or []
        out[key] = [c for c in cols if c not in drop_set]
    return out


def feature_counts_from_groups(groups: Dict[str, Any]) -> Dict[str, int]:
    phys = len(groups.get("physical") or [])
    writes = len(groups.get("writes") or [])
    last = len(groups.get("last_value") or [])
    net = len(groups.get("network") or [])
    return {
        "physical": phys,
        "protocol_writes": writes,
        "protocol_last_value": last,
        "protocol_total": writes + last,
        "network": net,
        "features_total": phys + writes + last + net,
    }


def build_selected_schema(
    base_schema: Dict[str, Any],
    groups_after: Dict[str, Any],
    dropped: List[str],
    attack_active: List[str],
    selected_csv: str,
) -> Dict[str, Any]:
    counts = feature_counts_from_groups(groups_after)
    return {
        "source_clean": base_schema.get("cleaned"),
        "selected": selected_csv.replace("\\", "/"),
        "n_rows": base_schema.get("n_rows"),
        "n_cols": counts["features_total"] + 1,
        "feature_counts": counts,
        "column_groups": groups_after,
        "dropped_zero_variance": dropped,
        "kept_train_silent_attack_active": attack_active,
        "phase1_dropped_alarms": base_schema.get("dropped_columns", []),
        "policies": {
            "log1p_writes": True,
            "outlier_removal": False,
            "var_epsilon": VAR_EPS,
        },
    }
