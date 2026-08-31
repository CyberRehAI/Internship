# Hourly Behavior Generalization

Train the stacked cascade on one clock hour; score the immediately following hour of the **same** operating regime. Not the Phase 10 AD leaderboard experiment.

Verdict rule: eval `% above threshold` ≤ 10 → **generalized**; otherwise **behavioral_drift**. `mahalanobis_ratio` = mean_eval / mean_train.

| Experiment | Train Hour | Test Hour | Regime | Mean Maha (train) | Mean Maha (eval) | Std (eval) | % Above Thr (eval) | Maha ratio | Recon LSTM/USAD/TranAD (eval) | Verdict |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| 2 | 11:00-12:00 | 12:00-13:00 | normal | 51.97 | 1102 | 891 | 100.00 | 21.21 | 77.58 / 0.01864 / 0.04566 | behavioral_drift |

## Per-experiment interpretation

### Experiment 2 (11:00-12:00 → 12:00-13:00, normal)

Eval-hour flags (100.00%) exceeded the 10% cutoff, indicating **behavioral drift** relative to the training hour under the fixed 95th-percentile threshold. Mahalanobis mean ratio (eval/train) = 21.21; elevated ratio supports distributional shift.
