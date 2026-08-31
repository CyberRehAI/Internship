# AI-TDP baselines package (Pipeline 1)

**Ops / code home** for external AD baselines (LSTM-AE, USAD, TranAD).

**Not the project source of truth.** Splits, dual-pipeline design, and metrics
policy are defined in the root [`README.md`](../README.md) (§6). If this doc
and the README disagree on science, **follow the README**.

## What this package does

| Piece | Path |
| :--- | :--- |
| Models | `baselines/models/` |
| Dataset (net / concat / domains) | `baselines/data/dataset.py` |
| Train CLIs | `baselines/train/train_*.py` |
| Shared eval | `baselines/eval/` |
| Colab guides | `baselines/docs/` |
| Colab notebooks | `baselines/notebooks/` |
| Pack zips | `python baselines/scripts/pack_colab.py` |
| Outputs | `baselines/outputs/{model_id}/`, `baselines/outputs/evaluation/` |

## Data (do not re-window)

Use Phase 3 NPZs:

```text
behavior/outputs/windows/{train,val,test}.npz
```

Or copy them into `baselines/data/windows/` for Colab. See `baselines/data/README.md`.

| Mode | Tensor | Dim |
| :--- | :--- | ---: |
| `net` | network only | 7 |
| `concat` | net ∥ proto ∥ phys | 194 |
| `domains` | separate `net` / `proto` / `phys` | 7 / 122 / 65 |

## Train (from repo root)

```powershell
cd D:\AI-TDP
python -m baselines.train.train_lstm_ae --mode net --epochs 50
python -m baselines.train.train_lstm_ae --mode concat --epochs 50
python -m baselines.train.train_usad --mode concat --epochs 50
python -m baselines.train.train_tranad --mode concat --epochs 50
```

## Experimental stacked cascade (not official hierarchy)

Single script: Network LSTM-AE → Protocol USAD (+ context) → Physical TranAD (+ context) → Mahalanobis on unified `z`.

```powershell
python -m baselines.train.train_stacked_cascade
python -m baselines.train.train_stacked_cascade --epochs 2 --patience 2 --cpu
```

Outputs only under `baselines/outputs/stacked_cascade/` (does **not** overwrite flat `lstm_ae_*` / `usad_*` / `tranad_*`).  
This is an **exploratory stacked AD cascade**, not Phase 10 flat baselines and not the proposed TCN→Transformer→GRU hierarchy.

## Hourly Behavior Generalization (additional experiment)

Same cascade architecture, trained **independently** on one clock hour and scored on the next hour (same regime). Measures whether the latent representation generalizes — **not** the Phase 10 AD leaderboard.

```powershell
python -m baselines.train.train_hourly_generalization
python -m baselines.train.train_hourly_generalization --epochs 2 --cpu
```

Outputs under `baselines/outputs/hourly_generalization/` (`experiment_1`…`4`, `summary.csv`, `hourly_generalization_report.md`).  
Does **not** modify `stacked_cascade` or flat baseline folders. Fixed epochs (no early stopping / no Val hour).

## Evaluate (coarse-label protocol)

```powershell
python -m baselines.eval.run_eval --model-id lstm_ae_net
python -m baselines.eval.run_eval --model-id lstm_ae_concat
python -m baselines.eval.run_eval --compare-all
```

Reports Val FPR, Test detection rate, and ROC/PR on **Val ∪ Test**.

## Colab

- All baselines: [`docs/COLAB_GUIDE.md`](docs/COLAB_GUIDE.md)
- **USAD first-time walkthrough:** [`docs/COLAB_USAD_GUIDE.md`](docs/COLAB_USAD_GUIDE.md) + notebook `notebooks/colab_usad.ipynb`
- **TranAD first-time walkthrough:** [`docs/COLAB_TRANAD_GUIDE.md`](docs/COLAB_TRANAD_GUIDE.md) + notebook `notebooks/colab_tranad.ipynb`
- **Stacked cascade (experimental):** [`docs/COLAB_STACKED_CASCADE_GUIDE.md`](docs/COLAB_STACKED_CASCADE_GUIDE.md) + `notebooks/colab_stacked_cascade.ipynb` · zip `dist/stacked_cascade_colab.zip`
