"""log1p writes + Train-only RobustScaler transforms (Phase 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

from behavior.data.splits import TIMESTAMP_COL, TRAIN_END, train_mask


def apply_log1p_writes(df: pd.DataFrame, write_cols: Sequence[str]) -> pd.DataFrame:
    """Return copy with log1p applied to writes_* only."""
    out = df.copy()
    for c in write_cols:
        out[c] = np.log1p(out[c].astype(np.float64))
    return out


def fit_transform_domains(
    df: pd.DataFrame,
    physical_cols: Sequence[str],
    write_cols: Sequence[str],
    last_value_cols: Sequence[str],
    network_cols: Sequence[str],
) -> Tuple[pd.DataFrame, Dict[str, RobustScaler], Dict[str, Any]]:
    """
    log1p writes, fit RobustScalers on Train seconds, transform all rows.

    Protocol features = writes (after log1p) + last_value, one scaler.
    """
    assert TIMESTAMP_COL in df.columns
    work = apply_log1p_writes(df, write_cols)
    t = work[TIMESTAMP_COL]
    fit_mask = train_mask(t)
    if fit_mask.any() and (t.loc[fit_mask] >= TRAIN_END).any():
        raise AssertionError("Train fit mask leaked t >= 12:00")

    protocol_cols: List[str] = list(write_cols) + list(last_value_cols)
    domains = {
        "physical": list(physical_cols),
        "protocol": protocol_cols,
        "network": list(network_cols),
    }

    scalers: Dict[str, RobustScaler] = {}
    info: Dict[str, Any] = {
        "n_fit_rows": int(fit_mask.sum()),
        "n_rows": int(len(work)),
        "log1p_writes": True,
        "scaler_type": "RobustScaler",
        "domains": {},
    }

    for name, cols in domains.items():
        scaler = RobustScaler()
        train_x = work.loc[fit_mask, cols].to_numpy(dtype=np.float64)
        scaler.fit(train_x)
        all_x = work[cols].to_numpy(dtype=np.float64)
        transformed = scaler.transform(all_x)
        work[cols] = transformed
        scalers[name] = scaler
        info["domains"][name] = {
            "n_features": len(cols),
            "columns": cols,
        }

    if not np.isfinite(work[protocol_cols + list(physical_cols) + list(network_cols)].to_numpy()).all():
        raise ValueError("Non-finite values after scaling")

    return work, scalers, info


def save_scalers(scalers: Dict[str, RobustScaler], out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, scaler in scalers.items():
        path = out_dir / f"{name}.joblib"
        joblib.dump(scaler, path)
        paths[name] = str(path).replace("\\", "/")
    return paths


def load_scalers(out_dir: Path) -> Dict[str, RobustScaler]:
    return {
        name: joblib.load(out_dir / f"{name}.joblib")
        for name in ("physical", "protocol", "network")
    }
