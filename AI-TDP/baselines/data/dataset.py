"""Baseline window dataset: net-only, concat, or separate domains."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

SplitName = Literal["train", "val", "test"]
FeatureMode = Literal["net", "concat", "domains"]


class SwatBaselineDataset(Dataset):
    """Loads Phase 3 split NPZ; returns ``x`` or domain tensors."""

    def __init__(self, npz_path: Path | str, mode: FeatureMode = "concat"):
        path = Path(npz_path)
        data = np.load(path, allow_pickle=False)
        self.net = data["net"]
        self.proto = data["proto"]
        self.phys = data["phys"]
        self.label = data["label"]
        self.end_time_ordinal = data["end_time_ordinal"]
        self.mode = mode
        assert len(self.net) == len(self.proto) == len(self.phys) == len(self.label)
        self.n_net = int(self.net.shape[-1])
        self.n_proto = int(self.proto.shape[-1])
        self.n_phys = int(self.phys.shape[-1])
        if mode == "net":
            self.n_features = self.n_net
        elif mode == "concat":
            self.n_features = self.n_net + self.n_proto + self.n_phys
        else:
            self.n_features = self.n_net + self.n_proto + self.n_phys
        self.T = int(self.net.shape[1])

    def __len__(self) -> int:
        return int(len(self.label))

    def _x_at(self, idx: int) -> np.ndarray:
        if self.mode == "net":
            return self.net[idx]
        return np.concatenate(
            [self.net[idx], self.proto[idx], self.phys[idx]], axis=-1
        )

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        meta = {
            "label": torch.tensor(int(self.label[idx]), dtype=torch.long),
            "end_time_ordinal": torch.tensor(
                int(self.end_time_ordinal[idx]), dtype=torch.long
            ),
        }
        if self.mode == "domains":
            return {
                "net": torch.from_numpy(np.asarray(self.net[idx], dtype=np.float32).copy()),
                "proto": torch.from_numpy(
                    np.asarray(self.proto[idx], dtype=np.float32).copy()
                ),
                "phys": torch.from_numpy(
                    np.asarray(self.phys[idx], dtype=np.float32).copy()
                ),
                **meta,
            }
        x = self._x_at(idx)
        return {
            "x": torch.from_numpy(np.asarray(x, dtype=np.float32).copy()),
            **meta,
        }


def resolve_windows_dir(windows_dir: Optional[Path | str] = None) -> Path:
    """Prefer explicit path; else Phase 3 outputs; else local baselines/data/windows."""
    if windows_dir is not None:
        return Path(windows_dir)
    root = Path(__file__).resolve().parents[2]
    phase3 = root / "behavior" / "outputs" / "windows"
    local = Path(__file__).resolve().parent / "windows"
    if (phase3 / "train.npz").is_file():
        return phase3
    if (local / "train.npz").is_file():
        return local
    return phase3


def make_loader(
    windows_dir: Path | str,
    split: SplitName,
    mode: FeatureMode = "concat",
    batch_size: int = 32,
    shuffle: bool = False,
    num_workers: int = 0,
) -> DataLoader:
    windows_dir = Path(windows_dir)
    ds = SwatBaselineDataset(windows_dir / f"{split}.npz", mode=mode)
    return DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
    )
