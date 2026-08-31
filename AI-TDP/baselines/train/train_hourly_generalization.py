"""
Hourly Behavior Generalization (additional experiment).

Train the stacked cascade on one clock hour; score the next hour.
Does NOT modify or replace the original stacked_cascade AD experiment.

Usage (from AI-TDP root):
  python -m baselines.train.train_hourly_generalization
  python -m baselines.train.train_hourly_generalization --epochs 2 --cpu
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.data.dataset import resolve_windows_dir
from baselines.data.hourly import (
    experiment_meta,
    filter_hour,
    list_experiment_ids,
    load_all_domain_windows,
    make_hourly_loader,
)
from baselines.detect.mahalanobis import MahalanobisDetector
from baselines.models.stacked_cascade import (
    StackedCascade,
    build_cascade,
    inject_context,
)
from baselines.train.common import (
    DEFAULT_OUTPUTS,
    ensure_windows,
    get_device,
    set_seed,
    write_config,
)

OUT_ROOT_NAME = "hourly_generalization"
DRIFT_PCT = 10.0


def _mse(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return ((a - b) ** 2).mean()


def _freeze(module: nn.Module) -> None:
    module.eval()
    for p in module.parameters():
        p.requires_grad = False


def _save_stage(path: Path, epoch: int, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"epoch": epoch, "model_state_dict": state}, path)


def train_stage1_lstm_fixed(
    cascade: StackedCascade,
    train_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    model = cascade.lstm.to(device)
    criterion = nn.MSELoss(reduction="mean")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: Dict[str, List[float]] = {"train_loss": []}

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        n = 0
        for batch in train_loader:
            x = batch["net"].to(device)
            optimizer.zero_grad(set_to_none=True)
            recon = model(x)
            loss = criterion(recon, x)
            loss.backward()
            optimizer.step()
            bs = x.size(0)
            running += float(loss.item()) * bs
            n += bs
        train_loss = running / max(n, 1)
        history["train_loss"].append(train_loss)
        if verbose:
            print(f"[stage1 LSTM] epoch {epoch:03d}/{epochs}  train={train_loss:.6f}")

    state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    _save_stage(out_dir / "stage1_lstm.pt", epochs, state)
    _freeze(model)
    return {"history": history, "final_epoch": epochs, "final_train_loss": history["train_loss"][-1]}


def train_stage2_usad_fixed(
    cascade: StackedCascade,
    train_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    cascade.lstm.eval()
    model = cascade.usad.to(device)
    opt_ae1 = torch.optim.Adam(
        list(model.encoder.parameters()) + list(model.decoder1.parameters()), lr=lr
    )
    opt_ae2 = torch.optim.Adam(
        list(model.encoder.parameters()) + list(model.decoder2.parameters()), lr=lr
    )
    history: Dict[str, List[float]] = {"train_loss": []}

    for epoch in range(1, epochs + 1):
        model.train()
        cascade.lstm.eval()
        running = 0.0
        n = 0
        n_epochs = float(epoch)
        for batch in train_loader:
            net = batch["net"].to(device)
            proto = batch["proto"].to(device)
            with torch.no_grad():
                z1 = cascade.lstm.encode(net)
            x = inject_context(proto, z1)

            w1 = model.forward_ae1(x)
            w2_from_w1 = model.forward_ae2(w1.detach())
            loss_ae1 = _mse(w1, x) + (1.0 / n_epochs) * _mse(x, w2_from_w1)
            opt_ae1.zero_grad(set_to_none=True)
            loss_ae1.backward()
            opt_ae1.step()

            w1 = model.forward_ae1(x)
            w2 = model.forward_ae2(x)
            loss_ae2 = _mse(w2, x) - (1.0 / n_epochs) * _mse(
                x, model.forward_ae2(w1.detach())
            )
            opt_ae2.zero_grad(set_to_none=True)
            loss_ae2.backward()
            opt_ae2.step()

            bs = x.size(0)
            running += float((loss_ae1 + loss_ae2).item()) * bs
            n += bs

        train_loss = running / max(n, 1)
        history["train_loss"].append(train_loss)
        if verbose:
            print(f"[stage2 USAD] epoch {epoch:03d}/{epochs}  train={train_loss:.6f}")

    state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    _save_stage(out_dir / "stage2_usad.pt", epochs, state)
    _freeze(model)
    return {"history": history, "final_epoch": epochs, "final_train_loss": history["train_loss"][-1]}


def train_stage3_tranad_fixed(
    cascade: StackedCascade,
    train_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    cascade.lstm.eval()
    cascade.usad.eval()
    model = cascade.tranad.to(device)
    criterion = nn.MSELoss(reduction="mean")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: Dict[str, List[float]] = {"train_loss": []}

    for epoch in range(1, epochs + 1):
        model.train()
        cascade.lstm.eval()
        cascade.usad.eval()
        running = 0.0
        n = 0
        for batch in train_loader:
            net = batch["net"].to(device)
            proto = batch["proto"].to(device)
            phys = batch["phys"].to(device)
            with torch.no_grad():
                z1 = cascade.lstm.encode(net)
                z2 = cascade.usad.encode(inject_context(proto, z1))
            x = inject_context(phys, z2)
            optimizer.zero_grad(set_to_none=True)
            recon = model(x)
            loss = criterion(recon, x)
            loss.backward()
            optimizer.step()
            bs = x.size(0)
            running += float(loss.item()) * bs
            n += bs

        train_loss = running / max(n, 1)
        history["train_loss"].append(train_loss)
        if verbose:
            print(f"[stage3 TranAD] epoch {epoch:03d}/{epochs}  train={train_loss:.6f}")

    state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    _save_stage(out_dir / "stage3_tranad.pt", epochs, state)
    model.eval()
    return {"history": history, "final_epoch": epochs, "final_train_loss": history["train_loss"][-1]}


@torch.no_grad()
def collect_latents_and_recon(
    cascade: StackedCascade,
    loader: DataLoader,
    device: torch.device,
) -> Dict[str, np.ndarray]:
    """Export z3 and per-window recon MSE for each stage."""
    cascade.eval()
    zs: List[np.ndarray] = []
    ordinals: List[np.ndarray] = []
    lstm_mse: List[float] = []
    usad_mse: List[float] = []
    tranad_mse: List[float] = []

    for batch in loader:
        net = batch["net"].to(device)
        proto = batch["proto"].to(device)
        phys = batch["phys"].to(device)

        z1 = cascade.lstm.encode(net)
        recon_net = cascade.lstm(net)
        lstm_per = ((recon_net - net) ** 2).mean(dim=(1, 2))

        x_proto = inject_context(proto, z1)
        z2 = cascade.usad.encode(x_proto)
        recon_proto = cascade.usad.forward_ae1(x_proto)
        usad_per = ((recon_proto - x_proto) ** 2).mean(dim=(1, 2))

        x_phys = inject_context(phys, z2)
        z3 = cascade.tranad.encode(x_phys)
        recon_phys = cascade.tranad(x_phys)
        tranad_per = ((recon_phys - x_phys) ** 2).mean(dim=(1, 2))

        zs.append(z3.cpu().numpy())
        ordinals.append(batch["end_time_ordinal"].cpu().numpy())
        lstm_mse.extend(lstm_per.cpu().numpy().tolist())
        usad_mse.extend(usad_per.cpu().numpy().tolist())
        tranad_mse.extend(tranad_per.cpu().numpy().tolist())

    return {
        "z": np.concatenate(zs, axis=0).astype(np.float32),
        "end_time_ordinal": np.concatenate(ordinals, axis=0).astype(np.int64),
        "recon_lstm": np.asarray(lstm_mse, dtype=np.float64),
        "recon_usad": np.asarray(usad_mse, dtype=np.float64),
        "recon_tranad": np.asarray(tranad_mse, dtype=np.float64),
    }


def _score_stats(scores: np.ndarray, threshold: float) -> Dict[str, float]:
    above = scores >= threshold
    return {
        "mean": float(scores.mean()),
        "median": float(np.median(scores)),
        "std": float(scores.std()),
        "pct_above_threshold": float(100.0 * above.mean()),
        "n_anomalous": int(above.sum()),
        "n_windows": int(len(scores)),
    }


def _verdict(pct_above_eval: float) -> str:
    return "generalized" if pct_above_eval <= DRIFT_PCT else "behavioral_drift"


def _plot_mahalanobis_hist(
    path: Path,
    score_train: np.ndarray,
    score_eval: np.ndarray,
    threshold: float,
) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(score_train, bins=40, alpha=0.55, label="train hour", density=True)
    ax.hist(score_eval, bins=40, alpha=0.55, label="eval hour", density=True)
    ax.axvline(threshold, color="black", ls="--", label=f"thr={threshold:.4g}")
    ax.set_xlabel("Mahalanobis distance")
    ax.set_ylabel("density")
    ax.set_title("Mahalanobis scores")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _plot_recon_hist(
    path: Path,
    train: Dict[str, np.ndarray],
    eval_: Dict[str, np.ndarray],
) -> None:
    keys = [("recon_lstm", "LSTM-AE"), ("recon_usad", "USAD"), ("recon_tranad", "TranAD")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for ax, (key, title) in zip(axes, keys):
        ax.hist(train[key], bins=30, alpha=0.55, label="train", density=True)
        ax.hist(eval_[key], bins=30, alpha=0.55, label="eval", density=True)
        ax.set_title(title)
        ax.set_xlabel("MSE")
        ax.set_ylabel("density")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _summary_row(metrics: Dict[str, Any]) -> Dict[str, Any]:
    tr = metrics["train"]
    ev = metrics["eval"]
    return {
        "experiment_id": metrics["experiment_id"],
        "train_hour": metrics["train_hour_label"],
        "eval_hour": metrics["eval_hour_label"],
        "regime": metrics["regime"],
        "n_train": tr["n_windows"],
        "n_eval": ev["n_windows"],
        "threshold": metrics["threshold"],
        "maha_mean_train": tr["mahalanobis"]["mean"],
        "maha_mean_eval": ev["mahalanobis"]["mean"],
        "maha_std_eval": ev["mahalanobis"]["std"],
        "maha_median_eval": ev["mahalanobis"]["median"],
        "pct_above_thr_train": tr["mahalanobis"]["pct_above_threshold"],
        "pct_above_thr_eval": ev["mahalanobis"]["pct_above_threshold"],
        "n_anomalous_eval": ev["mahalanobis"]["n_anomalous"],
        "mahalanobis_ratio": metrics["mahalanobis_ratio"],
        "recon_lstm_mean_train": tr["recon"]["lstm_mean"],
        "recon_usad_mean_train": tr["recon"]["usad_mean"],
        "recon_tranad_mean_train": tr["recon"]["tranad_mean"],
        "recon_lstm_mean_eval": ev["recon"]["lstm_mean"],
        "recon_usad_mean_eval": ev["recon"]["usad_mean"],
        "recon_tranad_mean_eval": ev["recon"]["tranad_mean"],
        "verdict": metrics["verdict"],
    }


def _write_experiment_results_md(path: Path, metrics: Dict[str, Any], epochs: int) -> None:
    """Human-readable per-experiment results sheet."""
    tr = metrics["train"]
    ev = metrics["eval"]
    tm = tr["mahalanobis"]
    em = ev["mahalanobis"]
    tr_r = tr["recon"]
    ev_r = ev["recon"]
    verdict = metrics["verdict"]
    pct = em["pct_above_threshold"]
    ratio = metrics["mahalanobis_ratio"]
    if verdict == "generalized":
        interp = (
            f"Eval-hour flags ({pct:.2f}%) stayed at or below the 10% drift cutoff, "
            "so the latent representation is treated as having **generalized** to the next hour."
        )
    else:
        interp = (
            f"Eval-hour flags ({pct:.2f}%) exceeded the 10% cutoff, indicating "
            "**behavioral drift** relative to the training hour under the fixed 95th-percentile threshold."
        )
    ratio_note = (
        "near 1 supports similarity of score scale."
        if ratio < 2.0
        else "elevated ratio supports distributional shift."
    )
    lines = [
        f"# Experiment {metrics['experiment_id']} results",
        "",
        f"- **Train hour:** {metrics['train_hour_label']} (hour {metrics['train_hour_id']})",
        f"- **Eval hour:** {metrics['eval_hour_label']} (hour {metrics['eval_hour_id']})",
        f"- **Regime:** {metrics['regime']}",
        f"- **Epochs (fixed):** {epochs}",
        f"- **Threshold:** {metrics['threshold']:.6g} (train Mahalanobis {metrics['quantile']:.2f} quantile)",
        f"- **Verdict:** `{verdict}`",
        "",
        "## Interpretation",
        "",
        f"{interp} Mahalanobis mean ratio (eval/train) = {ratio:.4g}; {ratio_note}",
        "",
        "## Window counts",
        "",
        f"| Split | n |",
        f"| :--- | ---: |",
        f"| Train hour | {tr['n_windows']} |",
        f"| Eval hour | {ev['n_windows']} |",
        "",
        "## Mahalanobis",
        "",
        "| Metric | Train | Eval |",
        "| :--- | ---: | ---: |",
        f"| Mean | {tm['mean']:.6g} | {em['mean']:.6g} |",
        f"| Median | {tm['median']:.6g} | {em['median']:.6g} |",
        f"| Std | {tm['std']:.6g} | {em['std']:.6g} |",
        f"| % above threshold | {tm['pct_above_threshold']:.2f} | {em['pct_above_threshold']:.2f} |",
        f"| n anomalous | {tm['n_anomalous']} | {em['n_anomalous']} |",
        "",
        f"**mahalanobis_ratio** (mean_eval / mean_train) = `{ratio:.6g}`",
        "",
        "## Mean reconstruction loss (MSE)",
        "",
        "| Stage | Train | Eval |",
        "| :--- | ---: | ---: |",
        f"| LSTM-AE | {tr_r['lstm_mean']:.6g} | {ev_r['lstm_mean']:.6g} |",
        f"| USAD | {tr_r['usad_mean']:.6g} | {ev_r['usad_mean']:.6g} |",
        f"| TranAD | {tr_r['tranad_mean']:.6g} | {ev_r['tranad_mean']:.6g} |",
        "",
        "## Artifacts",
        "",
        "- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`",
        "- `mahalanobis.npz` (includes `threshold`, `quantile`)",
        "- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`",
        "- `mahalanobis_hist.png`, `recon_hist.png`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, rows: List[Dict[str, Any]], metrics_list: List[Dict[str, Any]]) -> None:
    lines = [
        "# Hourly Behavior Generalization",
        "",
        "Train the stacked cascade on one clock hour; score the immediately following hour "
        "of the **same** operating regime. Not the Phase 10 AD leaderboard experiment.",
        "",
        "Verdict rule: eval `% above threshold` ≤ 10 → **generalized**; otherwise **behavioral_drift**. "
        "`mahalanobis_ratio` = mean_eval / mean_train.",
        "",
        "| Experiment | Train Hour | Test Hour | Regime | Mean Maha (train) | Mean Maha (eval) | Std (eval) | % Above Thr (eval) | Maha ratio | Recon LSTM/USAD/TranAD (eval) | Verdict |",
        "| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |",
    ]
    for r in rows:
        recon = (
            f"{r['recon_lstm_mean_eval']:.4g} / "
            f"{r['recon_usad_mean_eval']:.4g} / "
            f"{r['recon_tranad_mean_eval']:.4g}"
        )
        lines.append(
            f"| {r['experiment_id']} | {r['train_hour']} | {r['eval_hour']} | {r['regime']} | "
            f"{r['maha_mean_train']:.4g} | {r['maha_mean_eval']:.4g} | {r['maha_std_eval']:.4g} | "
            f"{r['pct_above_thr_eval']:.2f} | {r['mahalanobis_ratio']:.4g} | {recon} | {r['verdict']} |"
        )
    lines.extend(["", "## Per-experiment interpretation", ""])
    for m in metrics_list:
        pct = m["eval"]["mahalanobis"]["pct_above_threshold"]
        ratio = m["mahalanobis_ratio"]
        verdict = m["verdict"]
        if verdict == "generalized":
            drift_txt = (
                f"Eval-hour flags ({pct:.2f}%) stayed at or below the 10% drift cutoff, "
                "so the latent representation is treated as having **generalized** to the next hour."
            )
        else:
            drift_txt = (
                f"Eval-hour flags ({pct:.2f}%) exceeded the 10% cutoff, indicating "
                "**behavioral drift** relative to the training hour under the fixed 95th-percentile threshold."
            )
        ratio_txt = (
            f"Mahalanobis mean ratio (eval/train) = {ratio:.4g}"
            + (
                "; near 1 supports similarity of score scale."
                if ratio < 2.0
                else "; elevated ratio supports distributional shift."
            )
        )
        lines.append(
            f"### Experiment {m['experiment_id']} "
            f"({m['train_hour_label']} → {m['eval_hour_label']}, {m['regime']})"
        )
        lines.append("")
        lines.append(f"{drift_txt} {ratio_txt}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_one_experiment(
    *,
    exp_id: int,
    all_windows: Dict[str, np.ndarray],
    out_root: Path,
    device: torch.device,
    latent_dim: int,
    hidden_dim: int,
    batch_size: int,
    lr: float,
    epochs: int,
    seed: int,
    quantile: float,
    num_workers: int,
    verbose: bool,
) -> Dict[str, Any]:
    meta = experiment_meta(exp_id)
    train_h = int(meta["train_hour_id"])
    eval_h = int(meta["eval_hour_id"])
    exp_dir = out_root / f"experiment_{exp_id}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    train_arr = filter_hour(all_windows, train_h)
    eval_arr = filter_hour(all_windows, eval_h)
    print(
        f"\n=== Experiment {exp_id}: hour {train_h} ({meta['train_hour_label']}) -> "
        f"hour {eval_h} ({meta['eval_hour_label']}) [{meta['regime']}] ==="
    )
    print(f"n_train={len(train_arr['label'])}  n_eval={len(eval_arr['label'])}")

    train_loader = make_hourly_loader(
        train_arr, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    train_export = make_hourly_loader(
        train_arr, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    eval_loader = make_hourly_loader(
        eval_arr, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    set_seed(seed)
    n_net = int(train_arr["net"].shape[-1])
    n_proto = int(train_arr["proto"].shape[-1])
    n_phys = int(train_arr["phys"].shape[-1])
    T = int(train_arr["net"].shape[1])

    cascade = build_cascade(
        n_net=n_net,
        n_proto=n_proto,
        n_phys=n_phys,
        latent_dim=latent_dim,
        hidden_dim=hidden_dim,
    ).to(device)

    s1 = train_stage1_lstm_fixed(
        cascade, train_loader, device=device, lr=lr, epochs=epochs, out_dir=exp_dir, verbose=verbose
    )
    s2 = train_stage2_usad_fixed(
        cascade, train_loader, device=device, lr=lr, epochs=epochs, out_dir=exp_dir, verbose=verbose
    )
    s3 = train_stage3_tranad_fixed(
        cascade, train_loader, device=device, lr=lr, epochs=epochs, out_dir=exp_dir, verbose=verbose
    )

    torch.save(
        {
            "lstm": cascade.lstm.state_dict(),
            "usad": cascade.usad.state_dict(),
            "tranad": cascade.tranad.state_dict(),
            "latent_dim": latent_dim,
            "n_net": n_net,
            "n_proto": n_proto,
            "n_phys": n_phys,
            "experiment_id": exp_id,
        },
        exp_dir / "final.pt",
    )

    train_pack = collect_latents_and_recon(cascade, train_export, device)
    eval_pack = collect_latents_and_recon(cascade, eval_loader, device)

    detector = MahalanobisDetector(eps=1e-6).fit(train_pack["z"])
    score_train = detector.score(train_pack["z"]).astype(np.float64)
    score_eval = detector.score(eval_pack["z"]).astype(np.float64)
    threshold = float(np.quantile(score_train, quantile))
    detector.save(exp_dir / "mahalanobis.npz", threshold=threshold, quantile=quantile)

    np.savez_compressed(
        exp_dir / "embeddings.npz",
        z_train=train_pack["z"],
        score_train=score_train.astype(np.float32),
        end_time_ordinal_train=train_pack["end_time_ordinal"],
        recon_lstm_train=train_pack["recon_lstm"],
        recon_usad_train=train_pack["recon_usad"],
        recon_tranad_train=train_pack["recon_tranad"],
        z_eval=eval_pack["z"],
        score_eval=score_eval.astype(np.float32),
        end_time_ordinal_eval=eval_pack["end_time_ordinal"],
        recon_lstm_eval=eval_pack["recon_lstm"],
        recon_usad_eval=eval_pack["recon_usad"],
        recon_tranad_eval=eval_pack["recon_tranad"],
    )

    train_maha = _score_stats(score_train, threshold)
    eval_maha = _score_stats(score_eval, threshold)
    mean_train = train_maha["mean"]
    mean_eval = eval_maha["mean"]
    ratio = float(mean_eval / mean_train) if mean_train > 0 else float("nan")
    verdict = _verdict(eval_maha["pct_above_threshold"])

    def _recon_block(pack: Dict[str, np.ndarray]) -> Dict[str, float]:
        return {
            "lstm_mean": float(pack["recon_lstm"].mean()),
            "usad_mean": float(pack["recon_usad"].mean()),
            "tranad_mean": float(pack["recon_tranad"].mean()),
        }

    metrics: Dict[str, Any] = {
        **meta,
        "threshold": threshold,
        "quantile": quantile,
        "mahalanobis_ratio": ratio,
        "verdict": verdict,
        "train": {
            "n_windows": train_maha["n_windows"],
            "mahalanobis": train_maha,
            "recon": _recon_block(train_pack),
        },
        "eval": {
            "n_windows": eval_maha["n_windows"],
            "mahalanobis": eval_maha,
            "recon": _recon_block(eval_pack),
        },
    }

    (exp_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    row = _summary_row(metrics)
    _write_csv(exp_dir / "summary.csv", [row])
    _write_experiment_results_md(exp_dir / "results.md", metrics, epochs=epochs)

    _plot_mahalanobis_hist(
        exp_dir / "mahalanobis_hist.png", score_train, score_eval, threshold
    )
    _plot_recon_hist(exp_dir / "recon_hist.png", train_pack, eval_pack)

    history_all = {
        "experiment_id": exp_id,
        "stage1_lstm": s1,
        "stage2_usad": s2,
        "stage3_tranad": s3,
        "device": str(device),
    }
    (exp_dir / "history.json").write_text(json.dumps(history_all, indent=2), encoding="utf-8")

    write_config(
        exp_dir,
        {
            "role": "hourly_behavior_generalization",
            "note": "Additional experiment; does not replace stacked_cascade AD run.",
            **meta,
            "windows_T": T,
            "n_net": n_net,
            "n_proto": n_proto,
            "n_phys": n_phys,
            "latent_dim": latent_dim,
            "hidden_dim": hidden_dim,
            "batch_size": batch_size,
            "lr": lr,
            "epochs": epochs,
            "early_stopping": False,
            "seed": seed,
            "device": str(device),
            "quantile": quantile,
            "threshold": threshold,
            "n_train": int(len(train_arr["label"])),
            "n_eval": int(len(eval_arr["label"])),
            "verdict": verdict,
            "mahalanobis_ratio": ratio,
        },
    )
    print(
        f"Experiment {exp_id} done: verdict={verdict}  "
        f"pct_above_eval={eval_maha['pct_above_threshold']:.2f}  ratio={ratio:.4g}"
    )
    return metrics


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Hourly Behavior Generalization (stacked cascade, fixed epochs)"
    )
    p.add_argument("--windows-dir", type=Path, default=None)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: baselines/outputs/hourly_generalization",
    )
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--hidden-dim", type=int, default=64)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--quantile", type=float, default=0.95)
    p.add_argument(
        "--experiments",
        type=str,
        default="all",
        help="Comma list of experiment ids (default: all)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    windows_dir = resolve_windows_dir(args.windows_dir)
    ensure_windows(windows_dir)
    out_root = Path(args.out_dir) if args.out_dir else DEFAULT_OUTPUTS / OUT_ROOT_NAME
    out_root.mkdir(parents=True, exist_ok=True)

    if args.experiments.strip().lower() == "all":
        exp_ids = list(list_experiment_ids())
    else:
        exp_ids = [int(x.strip()) for x in args.experiments.split(",") if x.strip()]

    device = get_device(args.cpu)
    print(f"Device: {device}")
    print(f"Hourly Behavior Generalization -> {out_root}")
    print("(Does not modify stacked_cascade or flat baseline outputs)")

    all_windows = load_all_domain_windows(windows_dir)
    print(f"Merged windows: n={len(all_windows['label'])} T={all_windows['net'].shape[1]}")

    metrics_list: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    for exp_id in exp_ids:
        if exp_id not in set(list_experiment_ids()):
            raise ValueError(f"Unknown experiment id: {exp_id}")
        m = run_one_experiment(
            exp_id=exp_id,
            all_windows=all_windows,
            out_root=out_root,
            device=device,
            latent_dim=args.latent_dim,
            hidden_dim=args.hidden_dim,
            batch_size=args.batch_size,
            lr=args.lr,
            epochs=args.epochs,
            seed=args.seed + exp_id,
            quantile=args.quantile,
            num_workers=args.num_workers,
            verbose=True,
        )
        metrics_list.append(m)
        rows.append(_summary_row(m))

    _write_csv(out_root / "summary.csv", rows)
    _write_report(out_root / "hourly_generalization_report.md", rows, metrics_list)
    print(f"Wrote {out_root / 'summary.csv'}")
    print(f"Wrote {out_root / 'hourly_generalization_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
