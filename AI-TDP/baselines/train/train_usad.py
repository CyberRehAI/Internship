"""
Train USAD baseline (default: concat windows).

Usage (from AI-TDP root):
  python -m baselines.train.train_usad --mode concat
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.data.dataset import make_loader, resolve_windows_dir
from baselines.models.usad import USAD
from baselines.train.common import (
    DEFAULT_OUTPUTS,
    ensure_windows,
    export_scores,
    get_device,
    set_seed,
    write_config,
)


def _mse(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return ((a - b) ** 2).mean()


@torch.no_grad()
def evaluate_usad(model: USAD, loader, device: torch.device) -> float:
    model.eval()
    total = 0.0
    n = 0
    for batch in loader:
        x = batch["x"].to(device)
        s = model.anomaly_score(x)
        total += float(s.sum().item())
        n += x.size(0)
    return total / max(n, 1)


def train_usad(
    model: USAD,
    train_loader,
    val_loader,
    *,
    device: torch.device,
    lr: float,
    epochs: int,
    patience: int,
    out_dir: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    model = model.to(device)
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
    out_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        n = 0
        n_epochs = float(epoch)
        for batch in train_loader:
            x = batch["x"].to(device)
            # AE1: reconstruct x; AE2: reconstruct AE1(x); adversarial mix per USAD
            w1 = model.forward_ae1(x)
            w2 = model.forward_ae2(x)
            w2_from_w1 = model.forward_ae2(w1.detach())

            loss_ae1 = _mse(w1, x) + (1.0 / n_epochs) * _mse(x, w2_from_w1)
            opt_ae1.zero_grad(set_to_none=True)
            loss_ae1.backward()
            opt_ae1.step()

            w1 = model.forward_ae1(x)
            w2 = model.forward_ae2(x)
            loss_ae2 = _mse(w2, x) - (1.0 / n_epochs) * _mse(x, model.forward_ae2(w1.detach()))
            opt_ae2.zero_grad(set_to_none=True)
            loss_ae2.backward()
            opt_ae2.step()

            bs = x.size(0)
            running += float((loss_ae1 + loss_ae2).item()) * bs
            n += bs

        train_loss = running / max(n, 1)
        val_loss = evaluate_usad(model, val_loader, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        if verbose:
            print(f"epoch {epoch:03d}/{epochs}  train={train_loss:.6f}  val_score={val_loss:.6f}")

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            torch.save(
                {"epoch": epoch, "model_state_dict": best_state, "val_loss": best_val},
                out_dir / "best.pt",
            )
        else:
            stale += 1
            if stale >= patience:
                if verbose:
                    print(f"Early stop at epoch {epoch} (best epoch {best_epoch})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    result = {
        "history": history,
        "best_epoch": best_epoch,
        "best_val_loss": best_val,
        "device": str(device),
    }
    (out_dir / "history.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train USAD baseline")
    p.add_argument("--mode", choices=("net", "concat"), default="concat")
    p.add_argument("--windows-dir", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--hidden-dim", type=int, default=64)
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cpu", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    windows_dir = resolve_windows_dir(args.windows_dir)
    ensure_windows(windows_dir)
    model_id = f"usad_{args.mode}"
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUTPUTS / model_id

    set_seed(args.seed)
    device = get_device(args.cpu)
    print(f"Device: {device}  mode={args.mode}  windows={windows_dir}")

    train_loader = make_loader(
        windows_dir, "train", mode=args.mode, batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = make_loader(
        windows_dir, "val", mode=args.mode, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers,
    )
    test_loader = make_loader(
        windows_dir, "test", mode=args.mode, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers,
    )
    sample = next(iter(train_loader))["x"]
    n_features = int(sample.shape[-1])
    T = int(sample.shape[1])
    print(f"Window shape: (B, {T}, {n_features})")

    model = USAD(n_features=n_features, hidden_dim=args.hidden_dim, latent_dim=args.latent_dim)
    train_result = train_usad(
        model,
        train_loader,
        val_loader,
        device=device,
        lr=args.lr,
        epochs=args.epochs,
        patience=args.patience,
        out_dir=out_dir,
        verbose=True,
    )
    test_score = evaluate_usad(model, test_loader, device)
    print(f"Best val score: {train_result['best_val_loss']:.6f}")
    print(f"Test score (report only): {test_score:.6f}")

    emb_dir = out_dir / "embeddings"
    emb_counts = {}
    for split in ("train", "val", "test"):
        loader = make_loader(
            windows_dir, split, mode=args.mode, batch_size=args.batch_size, shuffle=False,
            num_workers=args.num_workers,
        )
        info = export_scores(model, loader, device, emb_dir / f"{split}.npz")
        emb_counts[split] = info
        print(f"Wrote embeddings {split}: n={info['n']}")

    write_config(
        out_dir,
        {
            "model": "USAD",
            "model_id": model_id,
            "mode": args.mode,
            "windows_dir": str(windows_dir).replace("\\", "/"),
            "out_dir": str(out_dir).replace("\\", "/"),
            "n_features": n_features,
            "T": T,
            "hidden_dim": args.hidden_dim,
            "latent_dim": args.latent_dim,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "epochs": args.epochs,
            "patience": args.patience,
            "seed": args.seed,
            "device": str(device),
            "best_epoch": train_result["best_epoch"],
            "best_val_loss": train_result["best_val_loss"],
            "test_score": test_score,
            "embedding_counts": emb_counts,
        },
    )
    print(f"Wrote {out_dir / 'config.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
