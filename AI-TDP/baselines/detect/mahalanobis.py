"""Mahalanobis distance detector on embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np


class MahalanobisDetector:
    """Fit mean / precision on Train embeddings; score = squared Mahalanobis."""

    def __init__(self, eps: float = 1e-6):
        self.eps = eps
        self.mean_: Optional[np.ndarray] = None
        self.cov_inv_: Optional[np.ndarray] = None
        self.threshold_: Optional[float] = None
        self.quantile_: Optional[float] = None

    def fit(self, z: np.ndarray) -> "MahalanobisDetector":
        z = np.asarray(z, dtype=np.float64)
        if z.ndim != 2:
            raise ValueError(f"z must be 2D (N, D), got {z.shape}")
        self.mean_ = z.mean(axis=0)
        centered = z - self.mean_
        n = max(z.shape[0], 2)
        cov = (centered.T @ centered) / (n - 1)
        d = cov.shape[0]
        cov = cov + self.eps * np.eye(d)
        self.cov_inv_ = np.linalg.pinv(cov)
        return self

    def score(self, z: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.cov_inv_ is None:
            raise RuntimeError("MahalanobisDetector not fitted")
        z = np.asarray(z, dtype=np.float64)
        centered = z - self.mean_
        # (x-μ)^T Σ^{-1} (x-μ) per row
        left = centered @ self.cov_inv_
        return np.sum(left * centered, axis=1).astype(np.float64)

    def save(
        self,
        path: Union[Path, str],
        *,
        threshold: Optional[float] = None,
        quantile: Optional[float] = None,
    ) -> None:
        if self.mean_ is None or self.cov_inv_ is None:
            raise RuntimeError("MahalanobisDetector not fitted")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, np.ndarray] = {
            "mean": self.mean_.astype(np.float64),
            "cov_inv": self.cov_inv_.astype(np.float64),
            "eps": np.asarray(self.eps, dtype=np.float64),
        }
        if threshold is not None:
            payload["threshold"] = np.asarray(threshold, dtype=np.float64)
        if quantile is not None:
            payload["quantile"] = np.asarray(quantile, dtype=np.float64)
        np.savez_compressed(path, **payload)

    @classmethod
    def load(cls, path: Union[Path, str]) -> "MahalanobisDetector":
        data = np.load(path, allow_pickle=False)
        obj = cls(eps=float(data["eps"]))
        obj.mean_ = np.asarray(data["mean"], dtype=np.float64)
        obj.cov_inv_ = np.asarray(data["cov_inv"], dtype=np.float64)
        obj.threshold_ = float(data["threshold"]) if "threshold" in data.files else None
        obj.quantile_ = float(data["quantile"]) if "quantile" in data.files else None
        return obj

    def to_dict(self) -> Dict[str, float]:
        return {
            "eps": float(self.eps),
            "latent_dim": int(self.mean_.shape[0]) if self.mean_ is not None else 0,
        }
