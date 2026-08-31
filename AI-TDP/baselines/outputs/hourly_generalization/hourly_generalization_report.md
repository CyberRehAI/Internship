# Hourly Behavior Generalization

Train the stacked cascade on one clock hour; score the immediately following hour of the **same** operating regime. Not the Phase 10 AD leaderboard experiment.

Verdict rule: eval `% above threshold` ≤ 10 → **generalized**; otherwise **behavioral_drift**. `mahalanobis_ratio` = mean_eval / mean_train.

| Experiment | Train Hour | Test Hour | Regime | Mean Maha (train) | Mean Maha (eval) | Std (eval) | % Above Thr (eval) | Maha ratio | Recon LSTM/USAD/TranAD (eval) | Verdict |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| 1 | 09:00-10:00 | 10:00-11:00 | normal | 31.34 | 547.2 | 244.7 | 100.00 | 17.46 | 79.99 / 12.78 / 0.1633 | behavioral_drift |
| 2 | 11:00-12:00 | 12:00-13:00 | normal | 30.97 | 559.5 | 355.8 | 100.00 | 18.07 | 78.28 / 0.02968 / 0.05689 | behavioral_drift |
| 3 | 13:00-14:00 | 14:00-15:00 | attack | 31.13 | 939.5 | 496.8 | 98.03 | 30.18 | 99.25 / 9420 / 0.1408 | behavioral_drift |
| 4 | 15:00-16:00 | 16:00-17:00 | attack | 31.25 | 411.5 | 336 | 89.47 | 13.17 | 78.66 / 9710 / 0.09546 | behavioral_drift |

## Per-experiment interpretation

### Experiment 1 (09:00-10:00 → 10:00-11:00, normal)

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 17.46; elevated ratio supports distributional shift.

### Experiment 2 (11:00-12:00 → 12:00-13:00, normal)

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 18.07; elevated ratio supports distributional shift.

### Experiment 3 (13:00-14:00 → 14:00-15:00, attack)

Eval-hour flags (98.03%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 30.18; elevated ratio supports distributional shift.

### Experiment 4 (15:00-16:00 → 16:00-17:00, attack)

Eval-hour flags (89.47%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 13.17; elevated ratio supports distributional shift.
