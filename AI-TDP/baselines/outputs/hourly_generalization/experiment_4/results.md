# Experiment 4 results

- **Train hour:** 15:00-16:00 (hour 7)
- **Eval hour:** 16:00-17:00 (hour 8)
- **Regime:** attack
- **Epochs (fixed):** 50
- **Threshold:** 83.7271 (train Mahalanobis 0.95 quantile)
- **Verdict:** `behavioral_drift`

## Interpretation

Eval-hour flags (89.47%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 13.17; elevated ratio supports distributional shift.

## Window counts

| Split | n |
| :--- | ---: |
| Train hour | 355 |
| Eval hour | 361 |

## Mahalanobis

| Metric | Train | Eval |
| :--- | ---: | ---: |
| Mean | 31.2495 | 411.502 |
| Median | 23.0933 | 255.548 |
| Std | 22.826 | 335.997 |
| % above threshold | 5.07 | 89.47 |
| n anomalous | 18 | 323 |

**mahalanobis_ratio** (mean_eval / mean_train) = `13.1683`

## Mean reconstruction loss (MSE)

| Stage | Train | Eval |
| :--- | ---: | ---: |
| LSTM-AE | 86.4287 | 78.6595 |
| USAD | 252871 | 9709.65 |
| TranAD | 4.04498 | 0.0954562 |

## Artifacts

- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`
- `mahalanobis.npz` (includes `threshold`, `quantile`)
- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`
- `mahalanobis_hist.png`, `recon_hist.png`
