"""Phase 2 EDA helpers: variance analysis, sparsity, and matplotlib plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TIMESTAMP_COL = "t_stamp"
TRAIN_END = pd.Timestamp("2026-03-11 12:00:00")
ATTACK_START = pd.Timestamp("2026-03-11 13:00:00")
VAR_EPS = 1e-12

KEY_PHYSICAL = ["LIT101.Pv", "FIT101.Pv", "MV101.Status", "LIT301.Pv", "FIT501.Pv"]


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[TIMESTAMP_COL] = pd.to_datetime(out[TIMESTAMP_COL], errors="raise")
    return out


def split_masks(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Train (<12:00), morning-before-attack (<13:00), afternoon (>=13:00)."""
    t = df[TIMESTAMP_COL]
    train = t < TRAIN_END
    morning = t < ATTACK_START
    afternoon = t >= ATTACK_START
    return train, morning, afternoon


def compute_variance_table(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
) -> pd.DataFrame:
    """Per-feature variance on full day and Train period; flag constants."""
    train_mask, _, _ = split_masks(df)
    rows = []
    train_df = df.loc[train_mask, feature_cols]
    full = df[feature_cols]
    for col in feature_cols:
        var_full = float(full[col].var(ddof=0))
        var_train = float(train_df[col].var(ddof=0)) if len(train_df) else 0.0
        full_const = var_full <= VAR_EPS
        train_const = var_train <= VAR_EPS
        attack_active = train_const and (not full_const)
        rows.append(
            {
                "feature": col,
                "var_full": var_full,
                "var_train": var_train,
                "full_day_constant": full_const,
                "train_constant": train_const,
                "train_constant_attack_active": attack_active,
                "mean_full": float(full[col].mean()),
                "mean_train": float(train_df[col].mean()) if len(train_df) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def write_sparsity(
    df: pd.DataFrame,
    write_cols: Sequence[str],
) -> pd.DataFrame:
    """Mean write counts ranked (sparsity / dominance)."""
    means = df[list(write_cols)].mean().sort_values(ascending=False)
    return pd.DataFrame(
        {
            "feature": means.index.astype(str),
            "mean_writes": means.values.astype(float),
            "pct_nonzero": (df[list(write_cols)] > 0).mean().loc[means.index].values,
        }
    )


def select_key_features(
    df: pd.DataFrame,
    write_cols: Sequence[str],
    network_cols: Sequence[str],
    n_top_writes: int = 5,
) -> List[str]:
    keys: List[str] = []
    for c in KEY_PHYSICAL:
        if c in df.columns:
            keys.append(c)
    top_w = (
        df[list(write_cols)].mean().sort_values(ascending=False).head(n_top_writes).index.tolist()
    )
    keys.extend(top_w)
    keys.extend([c for c in network_cols if c in df.columns])
    # unique preserve order
    seen = set()
    out = []
    for c in keys:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _period_series(df: pd.DataFrame, col: str) -> Tuple[np.ndarray, np.ndarray]:
    _, morning, afternoon = split_masks(df)
    return df.loc[morning, col].to_numpy(), df.loc[afternoon, col].to_numpy()


def plot_morning_vs_afternoon_box(
    df: pd.DataFrame,
    cols: Sequence[str],
    out_path: Path,
    max_cols: int = 12,
) -> None:
    cols = [c for c in cols if c in df.columns][:max_cols]
    if not cols:
        return
    n = len(cols)
    fig, axes = plt.subplots(n, 1, figsize=(8, 2.2 * n), squeeze=False)
    for i, col in enumerate(cols):
        ax = axes[i, 0]
        m, a = _period_series(df, col)
        ax.boxplot([m, a], showfliers=False)
        ax.set_xticklabels(["morning(<13h)", "afternoon(>=13h)"])
        ax.set_title(col)
        ax.set_ylabel("value")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_timelines(
    df: pd.DataFrame,
    cols: Sequence[str],
    out_path: Path,
    max_cols: int = 10,
) -> None:
    cols = [c for c in cols if c in df.columns][:max_cols]
    if not cols:
        return
    n = len(cols)
    fig, axes = plt.subplots(n, 1, figsize=(11, 1.8 * n), sharex=True, squeeze=False)
    t = df[TIMESTAMP_COL]
    for i, col in enumerate(cols):
        ax = axes[i, 0]
        ax.plot(t, df[col], lw=0.6, color="C0")
        ax.axvline(TRAIN_END, color="orange", ls="--", lw=1, label="Val start 12:00")
        ax.axvline(ATTACK_START, color="red", ls="--", lw=1, label="Attack 13:00")
        ax.set_ylabel(col, fontsize=8)
        if i == 0:
            ax.legend(loc="upper right", fontsize=7)
    axes[-1, 0].set_xlabel("t_stamp")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_correlation_heatmap(
    df: pd.DataFrame,
    cols: Sequence[str],
    out_path: Path,
    title: str,
) -> None:
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 2:
        return
    train_mask, _, _ = split_masks(df)
    sub = df.loc[train_mask, cols]
    corr = sub.corr()
    fig, ax = plt.subplots(figsize=(max(6, 0.35 * len(cols)), max(5, 0.35 * len(cols))))
    im = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=90, fontsize=6)
    ax.set_yticklabels(cols, fontsize=6)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_writes_sparsity(sparsity: pd.DataFrame, out_path: Path, top_n: int = 40) -> None:
    top = sparsity.head(top_n)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.22 * len(top))))
    ax.barh(top["feature"][::-1], top["mean_writes"][::-1], color="steelblue")
    ax.set_xlabel("mean writes / second")
    ax.set_title(f"Protocol write sparsity (top {len(top)} by mean)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def run_all_plots(
    df: pd.DataFrame,
    groups: Dict[str, List[str]],
    fig_dir: Path,
) -> Dict[str, str]:
    """Generate standard Phase 2 figures; return map name -> relative path."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    write_cols = groups.get("writes", [])
    network_cols = groups.get("network", [])
    physical = groups.get("physical", [])
    keys = select_key_features(df, write_cols, network_cols)

    paths: Dict[str, str] = {}
    p_box = fig_dir / "morning_vs_afternoon_boxplots.png"
    plot_morning_vs_afternoon_box(df, keys, p_box)
    paths["boxplots"] = str(p_box).replace("\\", "/")

    p_ts = fig_dir / "timelines_key_features.png"
    plot_timelines(df, keys, p_ts)
    paths["timelines"] = str(p_ts).replace("\\", "/")

    # Correlations: physical (all if <=40 else top by train var), writes top-20, network all
    train_mask, _, _ = split_masks(df)
    phys_for_corr = physical
    if len(phys_for_corr) > 40:
        v = df.loc[train_mask, phys_for_corr].var(ddof=0).sort_values(ascending=False)
        phys_for_corr = v.head(40).index.tolist()
    p_cphys = fig_dir / "corr_physical_train.png"
    plot_correlation_heatmap(df, phys_for_corr, p_cphys, "Physical corr (Train 09-12)")
    paths["corr_physical"] = str(p_cphys).replace("\\", "/")

    w_var = df.loc[train_mask, write_cols].var(ddof=0).sort_values(ascending=False)
    top_w = w_var.head(20).index.tolist()
    p_cw = fig_dir / "corr_writes_train_top20.png"
    plot_correlation_heatmap(df, top_w, p_cw, "Writes corr top-20 by Train var")
    paths["corr_writes"] = str(p_cw).replace("\\", "/")

    p_cnet = fig_dir / "corr_network_train.png"
    plot_correlation_heatmap(df, network_cols, p_cnet, "Network corr (Train 09-12)")
    paths["corr_network"] = str(p_cnet).replace("\\", "/")

    sparsity = write_sparsity(df, write_cols)
    p_sp = fig_dir / "writes_sparsity.png"
    plot_writes_sparsity(sparsity, p_sp)
    paths["writes_sparsity"] = str(p_sp).replace("\\", "/")

    return paths


def build_eda_payload(
    variance: pd.DataFrame,
    sparsity: pd.DataFrame,
    figure_paths: Dict[str, str],
    dropped: List[str],
    attack_active: List[str],
    feature_counts_before: Dict[str, int],
    feature_counts_after: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "phase": 2,
        "policies": {
            "drop_full_day_zero_variance": True,
            "keep_train_silent_attack_active": True,
            "outlier_removal": False,
            "log1p_writes": True,
            "window_T": 60,
            "window_stride": 10,
            "var_epsilon": VAR_EPS,
        },
        "feature_counts_before": feature_counts_before,
        "feature_counts_after": feature_counts_after,
        "n_dropped_zero_variance": len(dropped),
        "dropped_zero_variance": dropped,
        "n_train_silent_attack_active": len(attack_active),
        "kept_train_silent_attack_active": attack_active,
        "variance_table": variance.to_dict(orient="records"),
        "writes_sparsity_top20": sparsity.head(20).to_dict(orient="records"),
        "figures": figure_paths,
    }


def eda_payload_to_markdown(payload: Dict[str, Any]) -> str:
    fc_b = payload["feature_counts_before"]
    fc_a = payload["feature_counts_after"]
    lines = [
        "# SWaT.A12 Phase 2 EDA Summary",
        "",
        "**Phase:** 2 — Exploratory data analysis",
        "",
        "## Decisions for Phase 3",
        "",
        "| Decision | Value |",
        "| :--- | :--- |",
        "| Drop full-day zero-variance features | Yes |",
        "| Keep train-silent / attack-active features | Yes |",
        "| Statistical outlier removal (IQR/Z-score) | **No** |",
        "| `log1p` on `writes_*` | **Yes** |",
        "| Window `T` / stride | 60 / 10 |",
        "",
        "## Feature counts",
        "",
        "| Domain | Before | After |",
        "| :--- | ---: | ---: |",
        f"| Physical | {fc_b.get('physical')} | {fc_a.get('physical')} |",
        f"| Protocol writes | {fc_b.get('protocol_writes')} | {fc_a.get('protocol_writes')} |",
        f"| Protocol last_value | {fc_b.get('protocol_last_value')} | {fc_a.get('protocol_last_value')} |",
        f"| Network | {fc_b.get('network')} | {fc_a.get('network')} |",
        f"| **Total features** | {fc_b.get('features_total')} | {fc_a.get('features_total')} |",
        "",
        f"**Dropped (full-day zero variance):** {payload['n_dropped_zero_variance']}",
        "",
    ]
    for c in payload["dropped_zero_variance"]:
        lines.append(f"- `{c}`")
    lines.extend(
        [
            "",
            f"**Kept train-constant but attack-active:** {payload['n_train_silent_attack_active']}",
            "",
        ]
    )
    for c in payload["kept_train_silent_attack_active"]:
        lines.append(f"- `{c}`")
    lines.extend(
        [
            "",
            "## Protocol sparsity",
            "",
            "Top write tags by mean rate (supports `log1p` -- heavy skew / sparse tags):",
            "",
        ]
    )
    for row in payload.get("writes_sparsity_top20", [])[:10]:
        lines.append(
            f"- `{row['feature']}`: mean={row['mean_writes']:.4g}, pct_nonzero={row['pct_nonzero']:.4g}"
        )
    lines.extend(["", "## Figures", ""])
    for name, path in (payload.get("figures") or {}).items():
        lines.append(f"- **{name}:** `{path}`")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Variance computed with population variance (`ddof=0`); constant if `var <= 1e-12`.",
            "- Train window for correlations / train variance: `09:00-12:00`.",
            "- Attack period for morning vs afternoon plots: `t >= 13:00`.",
            "- Full variance tables live in `reports/swat/swat_eda_summary.json`.",
            "",
        ]
    )
    return "\n".join(lines)
