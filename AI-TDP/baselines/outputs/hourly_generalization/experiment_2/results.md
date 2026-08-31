# Experiment 2 results

- **Train hour:** 11:00-12:00 (hour 3)
- **Eval hour:** 12:00-13:00 (hour 4)
- **Regime:** normal
- **Epochs (fixed):** 50
- **Threshold:** 59.3927 (train Mahalanobis 0.95 quantile)
- **Verdict:** `behavioral_drift`

## Interpretation

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 18.07; elevated ratio supports distributional shift.

## Window counts

| Split | n |
| :--- | ---: |
| Train hour | 355 |
| Eval hour | 355 |

## Mahalanobis

| Metric | Train | Eval |
| :--- | ---: | ---: |
| Mean | 30.9686 | 559.534 |
| Median | 27.8525 | 440.571 |
| Std | 14.7454 | 355.837 |
| % above threshold | 5.07 | 100.00 |
| n anomalous | 18 | 355 |

**mahalanobis_ratio** (mean_eval / mean_train) = `18.0678`

## Mean reconstruction loss (MSE)

| Stage | Train | Eval |
| :--- | ---: | ---: |
| LSTM-AE | 95.3984 | 78.2816 |
| USAD | 0.0293773 | 0.0296786 |
| TranAD | 0.0106586 | 0.056892 |

## Artifacts

- `final.pt`, `stage1_lstm.pt`, `stage2_usad.pt`, `stage3_tranad.pt`
- `mahalanobis.npz` (includes `threshold`, `quantile`)
- `embeddings.npz`, `metrics.json`, `summary.csv`, `history.json`, `config.json`
- `mahalanobis_hist.png`, `recon_hist.png`
