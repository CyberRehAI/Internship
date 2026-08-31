# SWaT.A12 Phase 3 — Windows & Scaling Summary

**Phase:** 3 — Windows, scaling, validation split

## Config

| Item | Value |
| :--- | :--- |
| T / stride | 60 / 10 |
| log1p writes | True |
| Scaler | RobustScaler (fit on Train seconds) |
| n_fit_rows | 10800 |
| Physical dim | 65 |
| Protocol dim | 122 |
| Network dim | 7 |

## Window counts

| Split | N windows | start_time min | end_time max |
| :--- | ---: | :--- | :--- |
| train | 1075 | 2026-03-11 09:00:00 | 2026-03-11 11:59:59 |
| val | 355 | 2026-03-11 12:00:00 | 2026-03-11 12:59:59 |
| test | 1441 | 2026-03-11 13:00:00 | 2026-03-11 17:00:59 |

**Total windows kept:** 2871
**Candidates / discarded (boundary):** 2881 / 10

## Split rule

- Windows must be fully contained in Train / Val / Test (start **and** end).
- Boundary-straddling windows are discarded.

## Leakage checks

- Train fully in [09:00, 12:00): **True**
- Val fully in [12:00, 13:00): **True**
- Test fully in [13:00, 17:00:59]: **True**
- All OK: **True**

## DataLoader smoke test

- batch net shape: `[16, 60, 7]`
- batch proto shape: `[16, 60, 122]`
- batch phys shape: `[16, 60, 65]`

## Artifacts

- **config:** `D:/AI-TDP/behavior/outputs/config_windows.json`
- **scalers:** `{'physical': 'D:/AI-TDP/behavior/outputs/scalers/physical.joblib', 'protocol': 'D:/AI-TDP/behavior/outputs/scalers/protocol.joblib', 'network': 'D:/AI-TDP/behavior/outputs/scalers/network.joblib'}`
- **windows:** `{'train': 'D:/AI-TDP/behavior/outputs/windows/train.npz', 'val': 'D:/AI-TDP/behavior/outputs/windows/val.npz', 'test': 'D:/AI-TDP/behavior/outputs/windows/test.npz', 'meta': 'D:/AI-TDP/behavior/outputs/windows/meta.json'}`
- **report:** `D:/AI-TDP/reports/swat_phase3_windows_summary.md`
