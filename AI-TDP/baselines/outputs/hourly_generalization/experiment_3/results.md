# Experiment 3 results

- **Train hour:** 13:00-14:00 (hour 5)
- **Eval hour:** 14:00-15:00 (hour 6)
- **Regime:** attack
- **Epochs (fixed):** 50
- **Threshold:** 82.8465 (train Mahalanobis 0.95 quantile)
- **Verdict:** `behavioral_drift`

## Interpretation

Eval-hour flags (98.03%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 30.18; elevated ratio supports distributional shift.

## Window counts

| Split | n |
| :--- | ---: |
| Train hour | 355 |
| Eval hour | 355 |

## Mahalanobis

| Metric | Train | Eval |
| :--- | ---: | ---: |
| Mean | 31.1265 | 939.495 |
| Median | 24.5556 | 790.801 |
| Std | 22.3769 | 496.769 |
| % above threshold | 5.07 | 98.03 |
| n anomalous | 18 | 348 |

**mahalanobis_ratio** (mean_eval / mean_train) = `30.1832`

## Mean reconstruction loss (MSE)

| Stage | Train | Eval |
| :--- | ---: | ---: |
| LSTM-AE | 82.0981 | 99.2507 |
| USAD | 8732.11 | 9419.55 |
| TranAD | 2.90891 | 0.140767 |

## Artifacts

- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`
- `mahalanobis.npz` (includes `threshold`, `quantile`)
- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`
- `mahalanobis_hist.png`, `recon_hist.png`
