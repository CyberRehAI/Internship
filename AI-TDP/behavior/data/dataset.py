"""PyTorch Dataset for Phase 3 window tensors."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

SplitName = Literal["train", "val", "test"]


class SwatWindowDataset(Dataset):
    """Loads a split .npz produced by Phase 3."""

    def __init__(self, npz_path: Path | str, end_times: Optional[list] = None):
        path = Path(npz_path)
        data = np.load(path, allow_pickle=False)
        self.net = data["net"]
        self.proto = data["proto"]
        self.phys = data["phys"]
        self.label = data["label"]
        self.end_time_ordinal = data["end_time_ordinal"]
        self.indices = data["indices"] if "indices" in data.files else None
        self.end_times = end_times  # optional list aligned to this split order

        assert len(self.net) == len(self.proto) == len(self.phys) == len(self.label)

    def __len__(self) -> int:
        return int(len(self.label))

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = {
            "net": torch.from_numpy(self.net[idx].copy()),
            "proto": torch.from_numpy(self.proto[idx].copy()),
            "phys": torch.from_numpy(self.phys[idx].copy()),
            "label": torch.tensor(int(self.label[idx]), dtype=torch.long),
            "end_time_ordinal": torch.tensor(
                int(self.end_time_ordinal[idx]), dtype=torch.long
            ),
        }
        if self.end_times is not None:
            item["end_time"] = self.end_times[idx]
        return item


def end_times_for_split(meta_rows: list, split: SplitName) -> list:
    return [m["end_time"] for m in meta_rows if m["split"] == split]


def make_loader(
    windows_dir: Path | str,
    split: SplitName,
    batch_size: int = 32,
    shuffle: bool = False,
    num_workers: int = 0,
    meta_rows: Optional[list] = None,
) -> DataLoader:
    windows_dir = Path(windows_dir)
    npz_path = windows_dir / f"{split}.npz"
    end_times = None
    if meta_rows is not None:
        end_times = end_times_for_split(meta_rows, split)
    ds = SwatWindowDataset(npz_path, end_times=end_times)
    return DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
    )
