"""Deterministic cleaning for SWaT.A12 multilayer 1s table (Phase 1)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from behavior.data.columns import (
    DROP_ALARM_COLS,
    LAST_VALUE_COLS,
    NETWORK_COLS,
    TIMESTAMP_COL,
    WRITE_COLS,
    assert_expected_columns,
    physical_columns,
    protocol_columns,
)

EXPECTED_N_ROWS = 28860

ALARM_MAP = {
    "Active": 1,
    "Inactive": 0,
}


def _nan_rates(df: pd.DataFrame, cols: List[str]) -> Dict[str, float]:
    rates: Dict[str, float] = {}
    n = len(df)
    if n == 0:
        return {c: 0.0 for c in cols}
    for c in cols:
        if c in df.columns:
            rates[c] = float(df[c].isna().mean())
    return rates


def _encode_alarms(series: pd.Series) -> Tuple[pd.Series, Dict[str, Any]]:
    """Map Active/Inactive; other values (e.g. Bad Input) -> NaN. Return stats."""
    raw_counts = series.astype(str).value_counts(dropna=False).to_dict()
    if series.dtype.kind in "iufb":
        mapped = series.where(series.isin([0, 1]), other=pd.NA)
    else:
        mapped = series.map(ALARM_MAP)  # unknown / Bad Input -> NaN
    n_bad = int(mapped.isna().sum())
    out = mapped.astype("float64").ffill().fillna(0.0)
    return out, {
        "value_counts_before": {str(k): int(v) for k, v in raw_counts.items()},
        "n_non_active_inactive_or_na": n_bad,
    }


def clean_swat_multilayer(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Clean multilayer CSV according to README Phase 1 rules.

    Returns
    -------
    clean_df : DataFrame with t_stamp + numeric feature columns only
    report : dict suitable for JSON / Markdown summary
    """
    if TIMESTAMP_COL not in df.columns:
        raise KeyError(f"Required column missing: {TIMESTAMP_COL}")

    assert_expected_columns(df.columns)
    report: Dict[str, Any] = {
        "n_rows_in": int(len(df)),
        "n_cols_in": int(df.shape[1]),
        "dropped_columns": [],
        "alarm_encoding": {},
        "nan_rates_before": {},
        "nan_rates_after": {},
        "protocol_missingness_before_fill": {},
        "network_nan_filled": False,
        "n_network_nans_before": 0,
        "coercion_notes": [],
        "feature_counts": {},
        "column_groups": {},
    }

    work = df.copy()
    work[TIMESTAMP_COL] = pd.to_datetime(work[TIMESTAMP_COL], errors="raise")

    # --- Drop always-bad alarms ---
    dropped = [c for c in DROP_ALARM_COLS if c in work.columns]
    missing_drop = [c for c in DROP_ALARM_COLS if c not in work.columns]
    work = work.drop(columns=dropped, errors="ignore")
    report["dropped_columns"] = dropped
    report["drop_alarms_missing_from_input"] = missing_drop

    phys_cols = physical_columns(work.columns)
    alarm_cols = [c for c in phys_cols if c.endswith(".Alarm")]
    status_cols = [c for c in phys_cols if c.endswith(".Status")]
    speed_cols = [c for c in phys_cols if c.endswith(".Speed")]
    state_cols = [c for c in phys_cols if c.endswith("_STATE")]
    sensor_cols = [c for c in phys_cols if c.endswith(".Pv")]
    other_phys = [
        c
        for c in phys_cols
        if c not in alarm_cols + status_cols + speed_cols + state_cols + sensor_cols
    ]

    track_cols = [
        c
        for c in NETWORK_COLS + WRITE_COLS + LAST_VALUE_COLS + phys_cols
        if c in work.columns
    ]
    report["nan_rates_before"] = {
        k: v for k, v in _nan_rates(work, track_cols).items() if v > 0
    }

    # --- Encode remaining alarms ---
    for col in alarm_cols:
        encoded, stats = _encode_alarms(work[col])
        work[col] = encoded
        report["alarm_encoding"][col] = stats

    # --- Coerce Status / Speed / STATE / sensors ---
    # Known dirty token in historian: "Bad Input" -> NaN then ffill/0
    bad_input_counts: Dict[str, int] = {}
    coerce_targets = status_cols + speed_cols + state_cols + sensor_cols + other_phys
    for col in coerce_targets:
        if col not in work.columns:
            continue
        s = work[col]
        if s.dtype == object or s.dtype == "string":
            as_str = s.astype(str)
            n_bad_input = int((as_str == "Bad Input").sum())
            if n_bad_input:
                bad_input_counts[col] = n_bad_input
            s = s.where(as_str != "Bad Input", other=pd.NA)
        numeric = pd.to_numeric(s, errors="coerce")
        n_unparsed = int(numeric.isna().sum() - s.isna().sum())
        # After Bad Input -> NA, any remaining coerce-failures are unexpected
        if n_unparsed > 0:
            bad_mask = numeric.isna() & s.notna()
            samples = s.loc[bad_mask].astype(str).unique()[:20]
            raise TypeError(
                f"Unexpected non-numeric values in {col}; samples={list(samples)}"
            )
        n_na = int(numeric.isna().sum())
        if n_na:
            numeric = numeric.ffill().fillna(0.0)
        work[col] = numeric.astype(float)

    report["coercion_notes"].append(
        {
            "status_cols": status_cols,
            "speed_cols": speed_cols,
            "state_cols": state_cols,
            "sensor_cols": len(sensor_cols),
            "other_phys": other_phys,
            "bad_input_counts": bad_input_counts,
            "all_numeric_after_coerce": True,
        }
    )

    # --- Protocol ---
    write_na_before = {c: int(work[c].isna().sum()) for c in WRITE_COLS}
    last_na_before = {c: int(work[c].isna().sum()) for c in LAST_VALUE_COLS}
    report["protocol_missingness_before_fill"] = {
        "writes_total_na": int(sum(write_na_before.values())),
        "last_value_total_na": int(sum(last_na_before.values())),
        "writes_cols_with_na": {k: v for k, v in write_na_before.items() if v},
        "last_value_cols_with_na": {k: v for k, v in last_na_before.items() if v},
    }

    for c in WRITE_COLS:
        work[c] = pd.to_numeric(work[c], errors="raise").fillna(0).clip(lower=0)

    for c in LAST_VALUE_COLS:
        work[c] = pd.to_numeric(work[c], errors="raise").ffill().fillna(0)

    # --- Network ---
    net_na = int(work[NETWORK_COLS].isna().sum().sum())
    report["n_network_nans_before"] = net_na
    if net_na > 0:
        work[NETWORK_COLS] = work[NETWORK_COLS].fillna(0)
        report["network_nan_filled"] = True
    for c in NETWORK_COLS:
        work[c] = pd.to_numeric(work[c], errors="raise")

    if len(work) != EXPECTED_N_ROWS:
        report["row_count_warning"] = (
            f"Expected {EXPECTED_N_ROWS} rows, got {len(work)}"
        )

    # Column order: timestamp, physical, protocol, network
    phys_final = physical_columns(work.columns)
    ordered = (
        [TIMESTAMP_COL]
        + phys_final
        + protocol_columns()
        + NETWORK_COLS
    )
    # Keep only known columns (drop any unexpected extras silently into report)
    extras = [c for c in work.columns if c not in ordered]
    if extras:
        report["unexpected_columns_dropped"] = extras
        work = work.drop(columns=extras)
    clean = work[ordered].copy()

    # Final dtype check: all features numeric
    feature_cols = [c for c in clean.columns if c != TIMESTAMP_COL]
    non_numeric = [
        c for c in feature_cols if not pd.api.types.is_numeric_dtype(clean[c])
    ]
    if non_numeric:
        raise TypeError(f"Non-numeric feature columns remain: {non_numeric}")

    report["nan_rates_after"] = {
        k: v for k, v in _nan_rates(clean, feature_cols).items() if v > 0
    }
    report["n_rows_out"] = int(len(clean))
    report["n_cols_out"] = int(clean.shape[1])
    report["feature_counts"] = {
        "physical": len(phys_final),
        "protocol_writes": len(WRITE_COLS),
        "protocol_last_value": len(LAST_VALUE_COLS),
        "protocol_total": len(WRITE_COLS) + len(LAST_VALUE_COLS),
        "network": len(NETWORK_COLS),
        "features_total": len(feature_cols),
    }
    report["column_groups"] = {
        "timestamp": TIMESTAMP_COL,
        "physical": phys_final,
        "writes": WRITE_COLS,
        "last_value": LAST_VALUE_COLS,
        "network": NETWORK_COLS,
    }
    return clean, report


def report_to_markdown(report: Dict[str, Any]) -> str:
    """Render cleaning report dict as Markdown."""
    fc = report.get("feature_counts", {})
    lines = [
        "# SWaT.A12 Multilayer Cleaning Report",
        "",
        "**Phase:** 1 — Data cleaning",
        "",
        "## Summary",
        "",
        f"| Item | Value |",
        f"| :--- | ---: |",
        f"| Rows in | {report.get('n_rows_in')} |",
        f"| Rows out | {report.get('n_rows_out')} |",
        f"| Cols in | {report.get('n_cols_in')} |",
        f"| Cols out | {report.get('n_cols_out')} |",
        f"| Physical features | {fc.get('physical')} |",
        f"| Protocol features | {fc.get('protocol_total')} |",
        f"| Network features | {fc.get('network')} |",
        f"| Total features | {fc.get('features_total')} |",
        "",
        "## Dropped columns",
        "",
    ]
    dropped = report.get("dropped_columns") or []
    if dropped:
        for c in dropped:
            lines.append(f"- `{c}`")
    else:
        lines.append("- (none)")
    lines.extend(["", "## Alarm encoding", ""])
    for col, stats in (report.get("alarm_encoding") or {}).items():
        lines.append(f"### `{col}`")
        lines.append("")
        lines.append(f"- Non Active/Inactive (pre-impute NA count): {stats.get('n_non_active_inactive_or_na')}")
        lines.append(f"- Value counts before: `{stats.get('value_counts_before')}`")
        lines.append("")
    proto = report.get("protocol_missingness_before_fill") or {}
    lines.extend(
        [
            "## Protocol missingness (before fill)",
            "",
            f"- `writes_*` total NA: {proto.get('writes_total_na')}",
            f"- `last_value_*` total NA: {proto.get('last_value_total_na')}",
            "",
            "## Network",
            "",
            f"- NA cells before fill: {report.get('n_network_nans_before')}",
            f"- Filled with 0: {report.get('network_nan_filled')}",
            "",
            "## NaN rates",
            "",
            f"- Before (cols with NA): `{report.get('nan_rates_before')}`",
            f"- After (cols with NA): `{report.get('nan_rates_after')}`",
            "",
        ]
    )
    if report.get("row_count_warning"):
        lines.extend(["## Warnings", "", report["row_count_warning"], ""])
    return "\n".join(lines) + "\n"
