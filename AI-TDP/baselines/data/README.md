# Baseline window data

Baselines **reuse** Phase 3 artifacts. Do not rebuild windows here.

## Canonical location (local)

```text
../../behavior/outputs/windows/train.npz
../../behavior/outputs/windows/val.npz
../../behavior/outputs/windows/test.npz
```

Train scripts default to that path when run from the repo root.

## Colab / portable copy

Place the same three files in this folder:

```text
baselines/data/windows/train.npz
baselines/data/windows/val.npz
baselines/data/windows/test.npz
```

Or upload `baselines_windows.zip` from `python baselines/scripts/pack_colab.py`.

Each NPZ contains `net`, `proto`, `phys`, `label`, `end_time_ordinal` (and optional `indices`).
