"""
Train LSTM-AE baseline (net or concat).

Usage (from AI-TDP root):
  python -m baselines.train.train_lstm_ae --mode net
  python -m baselines.train.train_lstm_ae --mode concat
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.data.dataset import make_loader, resolve_windows_dir
from baselines.models.lstm_ae import LSTMAE
from baselines.train.common import (
    DEFAULT_OUTPUTS,
    ensure_windows,
    evaluate_recon_mse,
    export_scores,
    get_device,
    set_seed,
    train_reconstruction,
    write_config,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train LSTM-AE baseline")
    p.add_argument("--mode", choices=("net", "concat"), default="net")
    p.add_argument("--windows-dir", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--hidden-dim", type=int, default=64)
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--num-layers", type=int, default=1)
    p.add_argument("--dropout", type=float, default=0.0)
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
    model_id = f"lstm_ae_{args.mode}"
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

    model = LSTMAE(
        n_features=n_features,
        hidden_dim=args.hidden_dim,
        latent_dim=args.latent_dim,
        num_layers=args.num_layers,
        dropout=args.dropout,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    train_result = train_reconstruction(
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
    test_mse = evaluate_recon_mse(model, test_loader, device)
    print(f"Best val MSE: {train_result['best_val_loss']:.6f}")
    print(f"Test MSE (report only): {test_mse:.6f}")

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
            "model": "LSTMAE",
            "model_id": model_id,
            "mode": args.mode,
            "windows_dir": str(windows_dir).replace("\\", "/"),
            "out_dir": str(out_dir).replace("\\", "/"),
            "n_features": n_features,
            "T": T,
            "hidden_dim": args.hidden_dim,
            "latent_dim": args.latent_dim,
            "num_layers": args.num_layers,
            "dropout": args.dropout,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "epochs": args.epochs,
            "patience": args.patience,
            "seed": args.seed,
            "device": str(device),
            "best_epoch": train_result["best_epoch"],
            "best_val_loss": train_result["best_val_loss"],
            "test_mse": test_mse,
            "embedding_counts": emb_counts,
        },
    )
    print(f"Wrote {out_dir / 'config.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
