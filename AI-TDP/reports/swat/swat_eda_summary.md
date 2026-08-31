# SWaT.A12 Phase 2 EDA Summary

**Phase:** 2 — Exploratory data analysis

## Decisions for Phase 3

| Decision | Value |
| :--- | :--- |
| Drop full-day zero-variance features | Yes |
| Keep train-silent / attack-active features | Yes |
| Statistical outlier removal (IQR/Z-score) | **No** |
| `log1p` on `writes_*` | **Yes** |
| Window `T` / stride | 60 / 10 |

## Feature counts

| Domain | Before | After |
| :--- | ---: | ---: |
| Physical | 82 | 65 |
| Protocol writes | 81 | 81 |
| Protocol last_value | 81 | 41 |
| Network | 7 | 7 |
| **Total features** | 251 | 194 |

**Dropped (full-day zero variance):** 57

- `P207.Status`
- `P208.Status`
- `LS201.Alarm`
- `LS202.Alarm`
- `LSL203.Alarm`
- `P302.Status`
- `AIT401.Pv`
- `P402.Status`
- `P404.Status`
- `LS401.Alarm`
- `P502.Status`
- `P502.Speed`
- `P603.Status`
- `LSH602.Alarm`
- `LSL602.Alarm`
- `LSH603.Alarm`
- `LSL603.Alarm`
- `last_value_HMI_AIT201`
- `last_value_HMI_AIT203`
- `last_value_HMI_AIT301`
- `last_value_HMI_AIT302`
- `last_value_HMI_AIT303`
- `last_value_HMI_AIT401`
- `last_value_HMI_AIT501`
- `last_value_HMI_AIT502`
- `last_value_HMI_AIT503`
- `last_value_HMI_AIT504`
- `last_value_HMI_FIT101`
- `last_value_HMI_FIT102`
- `last_value_HMI_FIT301`
- `last_value_HMI_FIT401`
- `last_value_HMI_FIT501`
- `last_value_HMI_FIT502`
- `last_value_HMI_FIT503`
- `last_value_HMI_FIT504`
- `last_value_HMI_FIT601`
- `last_value_HMI_FIT602`
- `last_value_HMI_LIT301`
- `last_value_HMI_LIT401`
- `last_value_HMI_LIT602`
- `last_value_HMI_P2_PERMISSIVE`
- `last_value_HMI_P3_PERMISSIVE`
- `last_value_HMI_P4_PERMISSIVE`
- `last_value_HMI_P5_PERMISSIVE`
- `last_value_HMI_P5_STATE`
- `last_value_HMI_P6_PERMISSIVE`
- `last_value_HMI_PIT501`
- `last_value_HMI_PIT502`
- `last_value_HMI_PIT503`
- `last_value_HMI_PLANT`
- `last_value_HMI_PLANT_AUTO`
- `last_value_HMI_PLANT_RESET`
- `last_value_HMI_P_NAOCL_UF_DUTY`
- `last_value_HMI_P_RO_FEED_DUTY`
- `last_value_HMI_RO_HPP_SD`
- `last_value_HMI_SHUTDOWN_FLUSHING`
- `last_value_P2_P2078_AUTOINP`

**Kept train-constant but attack-active:** 107

- `P102.Status`
- `P202.Status`
- `P204.Status`
- `P206.Status`
- `MV301.Status`
- `MV303.Status`
- `P602.Status`
- `writes_HMI_AIT201`
- `writes_HMI_AIT202`
- `writes_HMI_AIT203`
- `writes_HMI_AIT301`
- `writes_HMI_AIT302`
- `writes_HMI_AIT303`
- `writes_HMI_AIT401`
- `writes_HMI_AIT402`
- `writes_HMI_AIT501`
- `writes_HMI_AIT502`
- `writes_HMI_AIT503`
- `writes_HMI_AIT504`
- `writes_HMI_DPIT301`
- `writes_HMI_FIT101`
- `writes_HMI_FIT102`
- `writes_HMI_FIT401`
- `writes_HMI_FIT501`
- `writes_HMI_FIT502`
- `writes_HMI_FIT503`
- `writes_HMI_FIT504`
- `writes_HMI_FIT601`
- `writes_HMI_FIT602`
- `writes_HMI_LIT101`
- `writes_HMI_LIT401`
- `writes_HMI_LIT601`
- `writes_HMI_LIT602`
- `writes_HMI_MV101`
- `writes_HMI_MV301`
- `writes_HMI_MV302`
- `writes_HMI_MV303`
- `writes_HMI_MV304`
- `writes_HMI_MV501`
- `writes_HMI_MV502`
- `writes_HMI_MV503`
- `writes_HMI_MV504`
- `writes_HMI_P101`
- `writes_HMI_P102`
- `writes_HMI_P201`
- `writes_HMI_P202`
- `writes_HMI_P203`
- `writes_HMI_P204`
- `writes_HMI_P205`
- `writes_HMI_P206`
- `writes_HMI_P207`
- `writes_HMI_P208`
- `writes_HMI_P301`
- `writes_HMI_P302`
- `writes_HMI_P401`
- `writes_HMI_P402`
- `writes_HMI_P403`
- `writes_HMI_P404`
- `writes_HMI_P501`
- `writes_HMI_P502`
- `writes_HMI_P5_STATE`
- `writes_HMI_P601`
- `writes_HMI_P603`
- `writes_HMI_P6_PERMISSIVE`
- `writes_HMI_PIT501`
- `writes_HMI_PIT502`
- `writes_HMI_PIT503`
- `writes_HMI_UV401`
- `last_value_HMI_AIT202`
- `last_value_HMI_AIT402`
- `last_value_HMI_DPIT301`
- `last_value_HMI_FIT201`
- `last_value_HMI_LIT101`
- `last_value_HMI_LIT601`
- `last_value_HMI_MV101`
- `last_value_HMI_MV201`
- `last_value_HMI_MV301`
- `last_value_HMI_MV302`
- `last_value_HMI_MV303`
- `last_value_HMI_MV304`
- `last_value_HMI_MV501`
- `last_value_HMI_MV502`
- `last_value_HMI_MV503`
- `last_value_HMI_MV504`
- `last_value_HMI_P101`
- `last_value_HMI_P102`
- `last_value_HMI_P201`
- `last_value_HMI_P202`
- `last_value_HMI_P203`
- `last_value_HMI_P204`
- `last_value_HMI_P205`
- `last_value_HMI_P206`
- `last_value_HMI_P207`
- `last_value_HMI_P208`
- `last_value_HMI_P301`
- `last_value_HMI_P302`
- `last_value_HMI_P401`
- `last_value_HMI_P402`
- `last_value_HMI_P403`
- `last_value_HMI_P404`
- `last_value_HMI_P501`
- `last_value_HMI_P502`
- `last_value_HMI_P601`
- `last_value_HMI_P602`
- `last_value_HMI_P603`
- `last_value_HMI_UV401`
- `last_value_P6_P602_AUTOINP`

## Protocol sparsity

Top write tags by mean rate (supports `log1p` -- heavy skew / sparse tags):

- `writes_HMI_PLANT`: mean=184.8, pct_nonzero=1
- `writes_HMI_PLANT_AUTO`: mean=178.1, pct_nonzero=1
- `writes_HMI_PLANT_RESET`: mean=177.2, pct_nonzero=1
- `writes_P2_P2078_AUTOINP`: mean=28.1, pct_nonzero=1
- `writes_HMI_SHUTDOWN_FLUSHING`: mean=25.43, pct_nonzero=1
- `writes_P6_P602_AUTOINP`: mean=22.98, pct_nonzero=1
- `writes_HMI_RO_HPP_SD`: mean=15.94, pct_nonzero=1
- `writes_HMI_LIT601`: mean=0.1506, pct_nonzero=0.01064
- `writes_HMI_P101`: mean=0.05558, pct_nonzero=0.02893
- `writes_HMI_P102`: mean=0.03777, pct_nonzero=0.01985

## Figures

- **boxplots:** `D:/AI-TDP/reports/eda/morning_vs_afternoon_boxplots.png`
- **timelines:** `D:/AI-TDP/reports/eda/timelines_key_features.png`
- **corr_physical:** `D:/AI-TDP/reports/eda/corr_physical_train.png`
- **corr_writes:** `D:/AI-TDP/reports/eda/corr_writes_train_top20.png`
- **corr_network:** `D:/AI-TDP/reports/eda/corr_network_train.png`
- **writes_sparsity:** `D:/AI-TDP/reports/eda/writes_sparsity.png`

## Notes

- Variance computed with population variance (`ddof=0`); constant if `var <= 1e-12`.
- Train window for correlations / train variance: `09:00-12:00`.
- Attack period for morning vs afternoon plots: `t >= 13:00`.
- Full variance tables live in `reports/swat_eda_summary.json`.
