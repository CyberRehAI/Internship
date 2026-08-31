"""Compatibility shim — prefer ``baselines.models`` (top-level package)."""

from baselines.models.lstm_ae import LSTMAE

# Re-export train helpers that older scripts imported from here
from baselines.train.common import (  # noqa: F401
    evaluate_recon_mse as evaluate_recon,
    export_scores as export_embeddings,
    train_reconstruction,
)

__all__ = ["LSTMAE", "train_reconstruction", "evaluate_recon", "export_embeddings"]
