"""Compatibility shim — use ``baselines.train.common``."""

from __future__ import annotations

from typing import Any, Dict, Optional

import torch.nn as nn
from torch.utils.data import DataLoader

from baselines.train.common import (
    evaluate_recon_mse,
    export_scores,
    train_reconstruction as _train_reconstruction,
)


def evaluate_recon(
    model: nn.Module,
    loader: DataLoader,
    domain: str,
    device,
    criterion=None,
) -> float:
    """Legacy API: domain key ignored if batch uses ``x``; supports old ``net`` batches."""
    # Adapt old loaders that yield net/proto/phys
    class _Adapt:
        def __init__(self, base, key):
            self.base = base
            self.key = key

        def __iter__(self):
            for batch in self.base:
                if "x" in batch:
                    yield batch
                else:
                    yield {
                        "x": batch[self.key],
                        "label": batch["label"],
                        "end_time_ordinal": batch["end_time_ordinal"],
                    }

    adapted = _Adapt(loader, domain)
    return evaluate_recon_mse(model, adapted, device)  # type: ignore[arg-type]


def train_reconstruction(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    domain: str = "net",
    device=None,
    lr: float = 1e-3,
    epochs: int = 50,
    patience: int = 8,
    out_dir=None,
    verbose: bool = True,
) -> Dict[str, Any]:
    class _Adapt:
        def __init__(self, base, key):
            self.base = base
            self.key = key

        def __iter__(self):
            for batch in self.base:
                if "x" in batch:
                    yield batch
                else:
                    yield {
                        "x": batch[self.key],
                        "label": batch["label"],
                        "end_time_ordinal": batch["end_time_ordinal"],
                    }

    return _train_reconstruction(
        model,
        _Adapt(train_loader, domain),  # type: ignore[arg-type]
        _Adapt(val_loader, domain),  # type: ignore[arg-type]
        device=device,
        lr=lr,
        epochs=epochs,
        patience=patience,
        out_dir=out_dir,
        verbose=verbose,
    )


def export_embeddings(
    model: nn.Module,
    loader: DataLoader,
    domain: str,
    device,
    out_path,
) -> Dict[str, int]:
    class _Adapt:
        def __init__(self, base, key):
            self.base = base
            self.key = key

        def __iter__(self):
            for batch in self.base:
                if "x" in batch:
                    yield batch
                else:
                    yield {
                        "x": batch[self.key],
                        "label": batch["label"],
                        "end_time_ordinal": batch["end_time_ordinal"],
                    }

    return export_scores(model, _Adapt(loader, domain), device, out_path)  # type: ignore[arg-type]
