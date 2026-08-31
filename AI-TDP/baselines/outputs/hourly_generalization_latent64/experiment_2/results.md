# Experiment 2 results

- **Train hour:** 11:00-12:00 (hour 3)
- **Eval hour:** 12:00-13:00 (hour 4)
- **Regime:** normal
- **Epochs (fixed):** 50
- **Threshold:** 96.8406 (train Mahalanobis 0.95 quantile)
- **Verdict:** `behavioral_drift`

## Interpretation

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 21.21; elevated ratio supports distributional shift.

## Window counts

| Split | n |
| :--- | ---: |
| Train hour | 355 |
| Eval hour | 355 |

## Mahalanobis

| Metric | Train | Eval |
| :--- | ---: | ---: |
| Mean | 51.9659 | 1102.07 |
| Median | 46.3603 | 862.236 |
| Std | 21.616 | 891.033 |
| % above threshold | 5.07 | 100.00 |
| n anomalous | 18 | 355 |

**mahalanobis_ratio** (mean_eval / mean_train) = `21.2076`

## Mean reconstruction loss (MSE)

| Stage | Train | Eval |
| :--- | ---: | ---: |
| LSTM-AE | 94.6058 | 77.5807 |
| USAD | 0.0178523 | 0.0186418 |
| TranAD | 0.00831414 | 0.0456585 |

## Artifacts

- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`
- `mahalanobis.npz` (includes `threshold`, `quantile`)
- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`
- `mahalanobis_hist.png`, `recon_hist.png`
