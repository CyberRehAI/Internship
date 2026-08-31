"""
Experimental stacked baseline cascade (NOT the official hierarchy).

  Network → LSTM-AE → z1
  Protocol ∥ z1 → USAD → z2
  Physical ∥ z2 → TranAD → z3
  Mahalanobis(z3) → anomaly score

Usage (from AI-TDP root):
  python -m baselines.train.train_stacked_cascade
  python -m baselines.train.train_stacked_cascade --epochs 2 --patience 2 --cpu
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.data.dataset import make_loader, resolve_windows_dir
from baselines.detect.mahalanobis import MahalanobisDetector
from baselines.eval.metrics import evaluate_embeddings
from baselines.eval.run_eval import _write_comparison
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

MODEL_ID = "stacked_cascade"


def _mse(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return ((a - b) ** 2).mean()


def _freeze(module: nn.Module) -> None:
    module.eval()
    for p in module.parameters():
        p.requires_grad = False


def _save_stage(path: Path, epoch: int, state: Dict[str, Any], val_loss: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"epoch": epoch, "model_state_dict": state, "val_loss": val_loss},
        path,
    )


# ----- Stage 1: LSTM-AE on net -----


def train_stage1_lstm(
    cascade: StackedCascade,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    patience: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    model = cascade.lstm.to(device)
    criterion = nn.MSELoss(reduction="mean")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    best_state: Optional[Dict[str, Any]] = None
    best_epoch = 0
    stale = 0

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

        model.eval()
        v_total = 0.0
        v_n = 0
        with torch.no_grad():
            for batch in val_loader:
                x = batch["net"].to(device)
                recon = model(x)
                loss = criterion(recon, x)
                v_total += float(loss.item()) * x.size(0)
                v_n += x.size(0)
        val_loss = v_total / max(v_n, 1)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        if verbose:
            print(
                f"[stage1 LSTM] epoch {epoch:03d}/{epochs}  "
                f"train={train_loss:.6f}  val={val_loss:.6f}"
            )

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            _save_stage(out_dir / "stage1_lstm.pt", epoch, best_state, best_val)
        else:
            stale += 1
            if stale >= patience:
                if verbose:
                    print(f"[stage1 LSTM] Early stop at {epoch} (best {best_epoch})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    _freeze(model)
    return {"history": history, "best_epoch": best_epoch, "best_val_loss": best_val}


# ----- Stage 2: USAD on proto ∥ z1 -----


@torch.no_grad()
def _eval_usad_score(
    cascade: StackedCascade, loader: DataLoader, device: torch.device
) -> float:
    cascade.lstm.eval()
    cascade.usad.eval()
    total = 0.0
    n = 0
    for batch in loader:
        net = batch["net"].to(device)
        proto = batch["proto"].to(device)
        z1 = cascade.lstm.encode(net)
        x = inject_context(proto, z1)
        s = cascade.usad.anomaly_score(x)
        total += float(s.sum().item())
        n += net.size(0)
    return total / max(n, 1)


def train_stage2_usad(
    cascade: StackedCascade,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    patience: int,
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
    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    best_state: Optional[Dict[str, Any]] = None
    best_epoch = 0
    stale = 0

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
        val_loss = _eval_usad_score(cascade, val_loader, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        if verbose:
            print(
                f"[stage2 USAD] epoch {epoch:03d}/{epochs}  "
                f"train={train_loss:.6f}  val_score={val_loss:.6f}"
            )

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            _save_stage(out_dir / "stage2_usad.pt", epoch, best_state, best_val)
        else:
            stale += 1
            if stale >= patience:
                if verbose:
                    print(f"[stage2 USAD] Early stop at {epoch} (best {best_epoch})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    _freeze(model)
    return {"history": history, "best_epoch": best_epoch, "best_val_loss": best_val}


# ----- Stage 3: TranAD on phys ∥ z2 -----


@torch.no_grad()
def _eval_tranad_mse(
    cascade: StackedCascade, loader: DataLoader, device: torch.device
) -> float:
    cascade.lstm.eval()
    cascade.usad.eval()
    cascade.tranad.eval()
    criterion = nn.MSELoss(reduction="mean")
    total = 0.0
    n = 0
    for batch in loader:
        net = batch["net"].to(device)
        proto = batch["proto"].to(device)
        phys = batch["phys"].to(device)
        z1 = cascade.lstm.encode(net)
        z2 = cascade.usad.encode(inject_context(proto, z1))
        x = inject_context(phys, z2)
        recon = cascade.tranad(x)
        loss = criterion(recon, x)
        total += float(loss.item()) * net.size(0)
        n += net.size(0)
    return total / max(n, 1)


def train_stage3_tranad(
    cascade: StackedCascade,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    patience: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    cascade.lstm.eval()
    cascade.usad.eval()
    model = cascade.tranad.to(device)
    criterion = nn.MSELoss(reduction="mean")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    best_state: Optional[Dict[str, Any]] = None
    best_epoch = 0
    stale = 0

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
        val_loss = _eval_tranad_mse(cascade, val_loader, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        if verbose:
            print(
                f"[stage3 TranAD] epoch {epoch:03d}/{epochs}  "
                f"train={train_loss:.6f}  val={val_loss:.6f}"
            )

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            _save_stage(out_dir / "stage3_tranad.pt", epoch, best_state, best_val)
        else:
            stale += 1
            if stale >= patience:
                if verbose:
                    print(f"[stage3 TranAD] Early stop at {epoch} (best {best_epoch})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return {"history": history, "best_epoch": best_epoch, "best_val_loss": best_val}


# ----- Export + Mahalanobis -----


@torch.no_grad()
def collect_latents(
    cascade: StackedCascade,
    loader: DataLoader,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    cascade.eval()
    zs: List[np.ndarray] = []
    labels: List[np.ndarray] = []
    ordinals: List[np.ndarray] = []
    for batch in loader:
        net = batch["net"].to(device)
        proto = batch["proto"].to(device)
        phys = batch["phys"].to(device)
        z = cascade.forward_z(net, proto, phys)
        zs.append(z.cpu().numpy())
        labels.append(batch["label"].cpu().numpy())
        ordinals.append(batch["end_time_ordinal"].cpu().numpy())
    return (
        np.concatenate(zs, axis=0).astype(np.float32),
        np.concatenate(labels, axis=0).astype(np.int64),
        np.concatenate(ordinals, axis=0).astype(np.int64),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Experimental stacked cascade: LSTM-AE -> USAD -> TranAD -> Mahalanobis"
    )
    p.add_argument("--windows-dir", type=Path, default=None)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: baselines/outputs/stacked_cascade",
    )
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--hidden-dim", type=int, default=64)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--quantile", type=float, default=0.95)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    windows_dir = resolve_windows_dir(args.windows_dir)
    ensure_windows(windows_dir)
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUTPUTS / MODEL_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    emb_dir = out_dir / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)

    set_seed(args.seed)
    device = get_device(args.cpu)
    print(f"Device: {device}")
    print(f"Experimental stacked cascade -> {out_dir}")
    print("(Does not overwrite flat lstm_ae / usad / tranad baselines)")

    train_loader = make_loader(
        windows_dir,
        "train",
        mode="domains",
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = make_loader(
        windows_dir,
        "val",
        mode="domains",
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    test_loader = make_loader(
        windows_dir,
        "test",
        mode="domains",
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    sample = next(iter(train_loader))
    n_net = int(sample["net"].shape[-1])
    n_proto = int(sample["proto"].shape[-1])
    n_phys = int(sample["phys"].shape[-1])
    T = int(sample["net"].shape[1])
    print(f"Domains: net={n_net} proto={n_proto} phys={n_phys} T={T}")
    print(
        f"Augmented: USAD in={n_proto + args.latent_dim}  "
        f"TranAD in={n_phys + args.latent_dim}"
    )

    cascade = build_cascade(
        n_net=n_net,
        n_proto=n_proto,
        n_phys=n_phys,
        latent_dim=args.latent_dim,
        hidden_dim=args.hidden_dim,
    ).to(device)

    print("=== Stage 1: LSTM-AE on Network ===")
    s1 = train_stage1_lstm(
        cascade,
        train_loader,
        val_loader,
        device=device,
        lr=args.lr,
        epochs=args.epochs,
        patience=args.patience,
        out_dir=out_dir,
        verbose=True,
    )

    print("=== Stage 2: USAD on Protocol + LSTM context ===")
    s2 = train_stage2_usad(
        cascade,
        train_loader,
        val_loader,
        device=device,
        lr=args.lr,
        epochs=args.epochs,
        patience=args.patience,
        out_dir=out_dir,
        verbose=True,
    )

    print("=== Stage 3: TranAD on Physical + USAD context ===")
    s3 = train_stage3_tranad(
        cascade,
        train_loader,
        val_loader,
        device=device,
        lr=args.lr,
        epochs=args.epochs,
        patience=args.patience,
        out_dir=out_dir,
        verbose=True,
    )

    torch.save(
        {
            "lstm": cascade.lstm.state_dict(),
            "usad": cascade.usad.state_dict(),
            "tranad": cascade.tranad.state_dict(),
            "latent_dim": args.latent_dim,
            "n_net": n_net,
            "n_proto": n_proto,
            "n_phys": n_phys,
        },
        out_dir / "best.pt",
    )
    print(f"Wrote {out_dir / 'best.pt'}")

    print("=== Export latents + Mahalanobis ===")
    # Deterministic export loaders (no shuffle)
    train_export = make_loader(
        windows_dir, "train", mode="domains", batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers,
    )
    z_train, y_train, o_train = collect_latents(cascade, train_export, device)
    z_val, y_val, o_val = collect_latents(cascade, val_loader, device)
    z_test, y_test, o_test = collect_latents(cascade, test_loader, device)

    detector = MahalanobisDetector(eps=1e-6).fit(z_train)
    detector.save(out_dir / "mahalanobis.npz")
    s_train = detector.score(z_train).astype(np.float32)
    s_val = detector.score(z_val).astype(np.float32)
    s_test = detector.score(z_test).astype(np.float32)

    for split, z, s, y, o in (
        ("train", z_train, s_train, y_train, o_train),
        ("val", z_val, s_val, y_val, o_val),
        ("test", z_test, s_test, y_test, o_test),
    ):
        path = emb_dir / f"{split}.npz"
        np.savez_compressed(
            path,
            z=z,
            score=s,
            recon_mse=s,
            label=y,
            end_time_ordinal=o,
        )
        print(f"Wrote embeddings {split}: n={len(y)} latent={z.shape[1]}")

    # Sibling of model out_dir (e.g. .../outputs/evaluation) so Colab Drive paths work
    eval_dir = out_dir.parent / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    metrics = evaluate_embeddings(
        emb_dir, quantile=args.quantile, model_id=MODEL_ID
    )
    metrics_path = eval_dir / f"{MODEL_ID}.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Wrote {metrics_path}")

    # Refresh comparison table from all eval JSONs
    all_rows = []
    for jp in sorted(eval_dir.glob("*.json")):
        all_rows.append(json.loads(jp.read_text(encoding="utf-8")))
    if all_rows:
        _write_comparison(all_rows, eval_dir / "comparison.md")
        print(f"Wrote {eval_dir / 'comparison.md'}")

    history_all = {
        "role": "experimental_stacked_baseline_cascade",
        "stage1_lstm": s1,
        "stage2_usad": s2,
        "stage3_tranad": s3,
        "device": str(device),
    }
    (out_dir / "history.json").write_text(
        json.dumps(history_all, indent=2), encoding="utf-8"
    )

    write_config(
        out_dir,
        {
            "model": "StackedCascade",
            "model_id": MODEL_ID,
            "role": "experimental_stacked_baseline_cascade",
            "note": (
                "NOT the official Phase 10 flat baselines; "
                "NOT the proposed TCN→Transformer→GRU hierarchy."
            ),
            "pipeline": "net→LSTM-AE→proto∥z1→USAD→phys∥z2→TranAD→z→Mahalanobis",
            "windows_dir": str(windows_dir).replace("\\", "/"),
            "out_dir": str(out_dir).replace("\\", "/"),
            "n_net": n_net,
            "n_proto": n_proto,
            "n_phys": n_phys,
            "T": T,
            "usad_n_features": n_proto + args.latent_dim,
            "tranad_n_features": n_phys + args.latent_dim,
            "latent_dim": args.latent_dim,
            "hidden_dim": args.hidden_dim,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "epochs": args.epochs,
            "patience": args.patience,
            "seed": args.seed,
            "device": str(device),
            "quantile": args.quantile,
            "stage1_best_epoch": s1["best_epoch"],
            "stage1_best_val_loss": s1["best_val_loss"],
            "stage2_best_epoch": s2["best_epoch"],
            "stage2_best_val_loss": s2["best_val_loss"],
            "stage3_best_epoch": s3["best_epoch"],
            "stage3_best_val_loss": s3["best_val_loss"],
            "mahalanobis": detector.to_dict(),
            "metrics": metrics,
        },
    )
    print(f"Wrote {out_dir / 'config.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
