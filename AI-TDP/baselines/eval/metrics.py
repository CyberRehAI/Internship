"""Coarse-label evaluation metrics for SWaT.A12 baselines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    precision_recall_fscore_support,
    roc_auc_score,
)


def _load_scores(npz_path: Path) -> np.ndarray:
    data = np.load(npz_path, allow_pickle=False)
    if "score" in data.files:
        return np.asarray(data["score"], dtype=np.float64)
    if "recon_mse" in data.files:
        return np.asarray(data["recon_mse"], dtype=np.float64)
    raise KeyError(f"No score/recon_mse in {npz_path}")


def evaluate_embeddings(
    embeddings_dir: Union[Path, str],
    *,
    quantile: float = 0.95,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Threshold on Val score quantile; metrics for coarse period labels.

    - Val FPR at threshold
    - Test detection rate (= recall when Test is all positive)
    - P/R/F1 and ROC/PR-AUC on Val∪Test (Val=0, Test=1)
    """
    embeddings_dir = Path(embeddings_dir)
    val_path = embeddings_dir / "val.npz"
    test_path = embeddings_dir / "test.npz"
    if not val_path.is_file() or not test_path.is_file():
        raise FileNotFoundError(f"Need val.npz and test.npz under {embeddings_dir}")

    s_val = _load_scores(val_path)
    s_test = _load_scores(test_path)
    thr = float(np.quantile(s_val, quantile))

    val_pred = s_val >= thr
    test_pred = s_test >= thr
    val_fpr = float(val_pred.mean())
    test_detection_rate = float(test_pred.mean())

    scores = np.concatenate([s_val, s_test])
    y_true = np.concatenate([np.zeros(len(s_val), dtype=np.int64), np.ones(len(s_test), dtype=np.int64)])
    y_pred = (scores >= thr).astype(np.int64)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    roc = float(roc_auc_score(y_true, scores))
    pr_auc = float(average_precision_score(y_true, scores))

    return {
        "model_id": model_id,
        "embeddings_dir": str(embeddings_dir).replace("\\", "/"),
        "quantile": quantile,
        "threshold": thr,
        "n_val": int(len(s_val)),
        "n_test": int(len(s_test)),
        "val_fpr": val_fpr,
        "test_detection_rate": test_detection_rate,
        "val_union_test": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "roc_auc": roc,
            "pr_auc": pr_auc,
        },
        "score_stats": {
            "val_mean": float(s_val.mean()),
            "val_std": float(s_val.std()),
            "test_mean": float(s_test.mean()),
            "test_std": float(s_test.std()),
        },
    }
