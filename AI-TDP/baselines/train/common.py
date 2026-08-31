"""Shared training / export helpers for baseline models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

DEFAULT_OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"


def get_device(force_cpu: bool = False) -> torch.device:
    if force_cpu or not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device("cuda")


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)


@torch.no_grad()
def evaluate_recon_mse(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> float:
    criterion = nn.MSELoss(reduction="mean")
    model.eval()
    total = 0.0
    n = 0
    for batch in loader:
        x = batch["x"].to(device)
        recon = model(x)
        loss = criterion(recon, x)
        bs = x.size(0)
        total += float(loss.item()) * bs
        n += bs
    return total / max(n, 1)


def train_reconstruction(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    device: torch.device,
    lr: float = 1e-3,
    epochs: int = 50,
    patience: int = 8,
    out_dir: Optional[Path] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """MSE reconstruction with early stop on Val loss; saves best.pt."""
    model = model.to(device)
    criterion = nn.MSELoss(reduction="mean")
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    best_state: Optional[Dict[str, Any]] = None
    best_epoch = 0
    stale = 0

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        running = 0.0
        n = 0
        for batch in train_loader:
            x = batch["x"].to(device)
            optimizer.zero_grad(set_to_none=True)
            recon = model(x)
            loss = criterion(recon, x)
            loss.backward()
            optimizer.step()
            bs = x.size(0)
            running += float(loss.item()) * bs
            n += bs
        train_loss = running / max(n, 1)
        val_loss = evaluate_recon_mse(model, val_loader, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        if verbose:
            print(f"epoch {epoch:03d}/{epochs}  train={train_loss:.6f}  val={val_loss:.6f}")

        if val_loss < best_val - 1e-8:
            best_val = val_loss
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
            if out_dir is not None:
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": best_state,
                        "val_loss": best_val,
                    },
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
    if out_dir is not None:
        (out_dir / "history.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


@torch.no_grad()
def export_scores(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    out_path: Path,
    score_fn: Optional[Callable[[nn.Module, torch.Tensor], torch.Tensor]] = None,
) -> Dict[str, int]:
    """Export per-window score, optional z, labels, timestamps."""
    model.eval()
    model = model.to(device)
    scores: List[np.ndarray] = []
    zs: List[np.ndarray] = []
    labels: List[np.ndarray] = []
    ordinals: List[np.ndarray] = []
    has_encode = hasattr(model, "encode")

    for batch in loader:
        x = batch["x"].to(device)
        if score_fn is not None:
            s = score_fn(model, x)
        elif hasattr(model, "anomaly_score"):
            s = model.anomaly_score(x)
        else:
            recon = model(x)
            s = ((recon - x) ** 2).mean(dim=(1, 2))
        scores.append(s.detach().cpu().numpy())
        labels.append(batch["label"].cpu().numpy())
        ordinals.append(batch["end_time_ordinal"].cpu().numpy())
        if has_encode:
            zs.append(model.encode(x).detach().cpu().numpy())

    score_arr = np.concatenate(scores, axis=0).astype(np.float32)
    label_arr = np.concatenate(labels, axis=0).astype(np.int64)
    ord_arr = np.concatenate(ordinals, axis=0).astype(np.int64)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, np.ndarray] = {
        "score": score_arr,
        "recon_mse": score_arr,
        "label": label_arr,
        "end_time_ordinal": ord_arr,
    }
    latent_dim = 0
    if zs:
        z_arr = np.concatenate(zs, axis=0).astype(np.float32)
        payload["z"] = z_arr
        latent_dim = int(z_arr.shape[1])

    np.savez_compressed(out_path, **payload)
    return {"n": int(len(label_arr)), "latent_dim": latent_dim}


def write_config(out_dir: Path, config: Dict[str, Any]) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "config.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def ensure_windows(windows_dir: Path) -> None:
    for split in ("train", "val", "test"):
        path = windows_dir / f"{split}.npz"
        if not path.is_file():
            raise FileNotFoundError(f"Missing window file: {path}")
