"""Hourly Behavior Generalization — window filtering helpers (no rebuild)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

Regime = Literal["normal", "attack"]

DAY = "2026-03-11"


@dataclass(frozen=True)
class HourSpec:
    hour_id: int
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    regime: Regime
    end_inclusive: bool = False


def _ts(h: int, m: int = 0, s: int = 0) -> pd.Timestamp:
    return pd.Timestamp(f"{DAY} {h:02d}:{m:02d}:{s:02d}")


HOUR_SPECS: Dict[int, HourSpec] = {
    1: HourSpec(1, "09:00-10:00", _ts(9), _ts(10), "normal"),
    2: HourSpec(2, "10:00-11:00", _ts(10), _ts(11), "normal"),
    3: HourSpec(3, "11:00-12:00", _ts(11), _ts(12), "normal"),
    4: HourSpec(4, "12:00-13:00", _ts(12), _ts(13), "normal"),
    5: HourSpec(5, "13:00-14:00", _ts(13), _ts(14), "attack"),
    6: HourSpec(6, "14:00-15:00", _ts(14), _ts(15), "attack"),
    7: HourSpec(7, "15:00-16:00", _ts(15), _ts(16), "attack"),
    8: HourSpec(
        8,
        "16:00-17:00",
        _ts(16),
        pd.Timestamp(f"{DAY} 17:00:59"),
        "attack",
        end_inclusive=True,
    ),
}

# (experiment_id, train_hour_id, eval_hour_id)
EXPERIMENTS: List[Tuple[int, int, int]] = [
    (1, 1, 2),
    (2, 3, 4),
    (3, 5, 6),
    (4, 7, 8),
]


def load_all_domain_windows(windows_dir: Path | str) -> Dict[str, np.ndarray]:
    """Merge train/val/test Phase 3 NPZs into one domain dict."""
    windows_dir = Path(windows_dir)
    nets: List[np.ndarray] = []
    protos: List[np.ndarray] = []
    physs: List[np.ndarray] = []
    labels: List[np.ndarray] = []
    ordinals: List[np.ndarray] = []
    for split in ("train", "val", "test"):
        path = windows_dir / f"{split}.npz"
        if not path.is_file():
            raise FileNotFoundError(f"Missing window file: {path}")
        data = np.load(path, allow_pickle=False)
        nets.append(np.asarray(data["net"], dtype=np.float32))
        protos.append(np.asarray(data["proto"], dtype=np.float32))
        physs.append(np.asarray(data["phys"], dtype=np.float32))
        labels.append(np.asarray(data["label"], dtype=np.int64))
        ordinals.append(np.asarray(data["end_time_ordinal"], dtype=np.int64))
    return {
        "net": np.concatenate(nets, axis=0),
        "proto": np.concatenate(protos, axis=0),
        "phys": np.concatenate(physs, axis=0),
        "label": np.concatenate(labels, axis=0),
        "end_time_ordinal": np.concatenate(ordinals, axis=0),
    }


def _hour_mask(
    end_ordinal: np.ndarray,
    *,
    T: int,
    hour: HourSpec,
) -> np.ndarray:
    ends = pd.to_datetime(end_ordinal)
    starts = ends - pd.Timedelta(seconds=int(T) - 1)
    if hour.end_inclusive:
        return (starts >= hour.start) & (ends <= hour.end)
    return (starts >= hour.start) & (ends < hour.end)


def filter_hour(
    arrays: Dict[str, np.ndarray],
    hour_id: int,
    *,
    T: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """Keep windows fully contained in the given clock hour."""
    if hour_id not in HOUR_SPECS:
        raise KeyError(f"Unknown hour_id={hour_id}")
    hour = HOUR_SPECS[hour_id]
    if T is None:
        T = int(arrays["net"].shape[1])
    mask = _hour_mask(arrays["end_time_ordinal"], T=T, hour=hour)
    n = int(mask.sum())
    if n == 0:
        raise RuntimeError(
            f"No windows fully contained in hour {hour_id} ({hour.label})"
        )
    return {k: v[mask] for k, v in arrays.items()}


class HourlyDomainDataset(Dataset):
    """Domain tensors for hourly generalization (same keys as mode=domains)."""

    def __init__(self, arrays: Dict[str, np.ndarray]):
        self.net = np.asarray(arrays["net"], dtype=np.float32)
        self.proto = np.asarray(arrays["proto"], dtype=np.float32)
        self.phys = np.asarray(arrays["phys"], dtype=np.float32)
        self.label = np.asarray(arrays["label"], dtype=np.int64)
        self.end_time_ordinal = np.asarray(arrays["end_time_ordinal"], dtype=np.int64)
        assert len(self.net) == len(self.proto) == len(self.phys) == len(self.label)

    def __len__(self) -> int:
        return int(len(self.label))

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return {
            "net": torch.from_numpy(self.net[idx].copy()),
            "proto": torch.from_numpy(self.proto[idx].copy()),
            "phys": torch.from_numpy(self.phys[idx].copy()),
            "label": torch.tensor(int(self.label[idx]), dtype=torch.long),
            "end_time_ordinal": torch.tensor(
                int(self.end_time_ordinal[idx]), dtype=torch.long
            ),
        }


def make_hourly_loader(
    arrays: Dict[str, np.ndarray],
    *,
    batch_size: int = 32,
    shuffle: bool = False,
    num_workers: int = 0,
) -> DataLoader:
    ds = HourlyDomainDataset(arrays)
    return DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
    )


def experiment_meta(exp_id: int) -> Dict[str, Any]:
    for eid, train_h, eval_h in EXPERIMENTS:
        if eid == exp_id:
            th = HOUR_SPECS[train_h]
            eh = HOUR_SPECS[eval_h]
            if th.regime != eh.regime:
                raise RuntimeError(f"Regime mismatch for experiment {exp_id}")
            return {
                "experiment_id": exp_id,
                "train_hour_id": train_h,
                "eval_hour_id": eval_h,
                "train_hour_label": th.label,
                "eval_hour_label": eh.label,
                "regime": th.regime,
            }
    raise KeyError(f"Unknown experiment_id={exp_id}")


def list_experiment_ids() -> Sequence[int]:
    return [e[0] for e in EXPERIMENTS]
