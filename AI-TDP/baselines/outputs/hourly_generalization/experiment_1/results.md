# Experiment 1 results

- **Train hour:** 09:00-10:00 (hour 1)
- **Eval hour:** 10:00-11:00 (hour 2)
- **Regime:** normal
- **Epochs (fixed):** 50
- **Threshold:** 93.9176 (train Mahalanobis 0.95 quantile)
- **Verdict:** `behavioral_drift`

## Interpretation

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 17.46; elevated ratio supports distributional shift.

## Window counts

| Split | n |
| :--- | ---: |
| Train hour | 355 |
| Eval hour | 355 |

## Mahalanobis

| Metric | Train | Eval |
| :--- | ---: | ---: |
| Mean | 31.345 | 547.233 |
| Median | 21.6363 | 505.166 |
| Std | 28.2986 | 244.673 |
| % above threshold | 5.07 | 100.00 |
| n anomalous | 18 | 355 |

**mahalanobis_ratio** (mean_eval / mean_train) = `17.4584`

## Mean reconstruction loss (MSE)

| Stage | Train | Eval |
| :--- | ---: | ---: |
| LSTM-AE | 88.3579 | 79.9883 |
| USAD | 8.30007e+07 | 12.7763 |
| TranAD | 158.227 | 0.163266 |

## Artifacts

- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`
- `mahalanobis.npz` (includes `threshold`, `quantile`)
- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`
- `mahalanobis_hist.png`, `recon_hist.png`
