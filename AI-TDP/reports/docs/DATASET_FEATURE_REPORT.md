# Feature Inventory Report: SWaT, ELEGANT, IEC 60870-5-104

**Date:** 2026-07-16 (updated with local SWaT.A12 OT historian)  
**Workspace:** `AI-TDP`  
**Purpose:** Document local data, file formats, and complete feature lists.

---

## Executive summary

| Dataset | Local status | Primary modality | Ready ML features? | Feature count |
| :--- | :--- | :--- | :--- | :--- |
| **IEC 60870-5-104** | **Yes** — balanced CSVs + 3 attack packages | Network flows + PCAPs | **Yes** (supervised) | CIC **84** cols; custom **112** / **119** |
| **ELEGANT (PLC DoS/MiTM)** | **Yes** — archives + extracted flow CSVs | Raw PCAP → flow CSV | **Yes** (supervised) | **78** flow features |
| **SWaT.A12** | **Yes** — OT historian CSV | Process sensors / actuators / alarms | **Yes** (unsupervised / process AD) | **87** columns (no attack label) |

**Recommendation:** use IEC-104 / ELEGANT for supervised network IDS; use SWaT.A12 for process-level anomaly detection / forecasting (no `Normal/Attack` column in this export).

**Artifacts**

| Path | Content |
| :--- | :--- |
| `reports/DATASET_FEATURE_REPORT.md` | This report |
| `reports/swat_feature_inventory.json` | SWaT.A12 column inventory |
| `reports/iec104_feature_inventory.json` | Balanced CSV schemas |
| `reports/iec104_attack_packages_inventory.json` | Per-entity attack package CSVs |
| `reports/elegant_feature_inventory.json` | Archive list + PCAP analyses |
| `data/DOWNLOAD_STATUS.md` | Download / extraction status |

---

## 1. IEC 60870-5-104 Intrusion Detection Dataset

### Local layout

```
data/iec104/
  ReadMe.pdf
  balanced/.../iec104_train_test_csvs/          # ML-ready balanced train/test
  20200425_UOWM_IEC104_Dataset_m_sp_na_1_DoS/  # DoS (M_SP_NA_1)
  20200605_UOWM_IEC104_Dataset_c_rd_na_1/      # Unauthorized read (C_RD_NA_1)
  20200608_UOWM_IEC104_Dataset_mitm_drop/      # MITM packet drop
```

### 1A. Balanced train/test CSVs (earlier inventory)

Timeout folders: **15 / 30 / 60 / 90 / 120 / 180** s × CIC + custom.

| Split (timeout=60s) | Rows | Columns | Classes |
| :--- | ---: | ---: | ---: |
| CICFlowMeter train | 5,904 | **84** | 12 labels × 492 |
| Custom IEC-104 train | 5,904 | **112** | 12 labels × 492 |

**12 balanced labels:** `NORMAL`, `c_ci_na_1`, `c_ci_na_1_DoS`, `c_rd_na_1`, `c_rd_na_1_DoS`, `c_rp_na_1`, `c_rp_na_1_DoS`, `c_sc_na_1`, `c_sc_na_1_DoS`, `c_se_na_1`, `c_se_na_1_DoS`, `m_sp_na_1_DoS`  
(`mitm_drop` is **not** in balanced CSVs; only in attack package below.)

---

### 1B. New attack packages (verified on disk)

Each package is organized **per entity** (iecserver1–7, qtester, and sometimes attacker1–3). Typical files per entity:

| File pattern | Kind | Features |
| :--- | :--- | :--- |
| `*.pcap` | Full capture | Raw packets |
| `*_iec104_only.pcap` | IEC-104 filtered | Raw packets |
| `*.pcap_Flow.csv` | CICFlowMeter | **84** columns |
| `*_iec104_only.pcapiec104_network_flow_leayer.csv` | Custom parser | **119** columns |
| `*.png` | Attack diagram | — |

#### Package summary

| Package | Entities | CIC CSVs | Custom CSVs | Approx CIC rows | Labels seen |
| :--- | ---: | ---: | ---: | ---: | :--- |
| `m_sp_na_1_DoS` | 8 | 16 | 8 | ~152k | `m_sp_na_1_DoS`, `NORMAL` |
| `c_rd_na_1` | 11 | 22 | 11 | ~362k | `c_rd_na_1`, `NORMAL` |
| `mitm_drop` | 11 | 11 | **0** | ~383k | `mitm_drop`, `NORMAL` |

> **Note:** `mitm_drop` only ships CICFlowMeter CSVs (no custom IEC-104 flow CSVs), which matches a drop/filter attack that disrupts IEC-104 sessions.

---

### Feature set A — CICFlowMeter (83 + Label = 84)

Same schema in balanced files and attack-package `*.pcap_Flow.csv`:

| # | Feature | # | Feature |
| ---: | :--- | ---: | :--- |
| 1 | Flow ID | 43 | Fwd Pkts/s |
| 2 | Src IP | 44 | Bwd Pkts/s |
| 3 | Src Port | 45 | Pkt Len Min |
| 4 | Dst IP | 46 | Pkt Len Max |
| 5 | Dst Port | 47 | Pkt Len Mean |
| 6 | Protocol | 48 | Pkt Len Std |
| 7 | Timestamp | 49 | Pkt Len Var |
| 8 | Flow Duration | 50 | FIN Flag Cnt |
| 9 | Tot Fwd Pkts | 51 | SYN Flag Cnt |
| 10 | Tot Bwd Pkts | 52 | RST Flag Cnt |
| 11 | TotLen Fwd Pkts | 53 | PSH Flag Cnt |
| 12 | TotLen Bwd Pkts | 54 | ACK Flag Cnt |
| 13–20 | Fwd/Bwd Pkt Len Max/Min/Mean/Std | 55–57 | URG / CWE / ECE Flag |
| 21–22 | Flow Byts/s, Flow Pkts/s | 58 | Down/Up Ratio |
| 23–36 | Flow/Fwd/Bwd IAT Tot/Mean/Std/Max/Min | 59–61 | Pkt/Seg Size Avg |
| 37–40 | Fwd/Bwd PSH/URG Flags | 62–67 | Bulk rate avgs |
| 41–42 | Fwd/Bwd Header Len | 68–75 | Subflow / Win / Seg Size |
| | | 76–83 | Active/Idle Mean/Std/Max/Min |
| | | **84** | **Label** |

Drop before training: `Flow ID`, `Src IP`, `Dst IP`, `Timestamp` (and often ports).

---

### Feature set B — Custom IEC-104 (two variants)

#### B1. Balanced CSVs — **112** columns (no flow identity fields)

Starts at idle/active/IAT stats → IEC rates/APDU → I/S/U message counts → TCP flags → COT → TypeID → `Label`.  
Full list: `reports/iec104_feature_inventory.json` → `custom_60_train.columns`.

#### B2. Per-entity attack-package CSVs — **119** columns

Verified from `*iec104_network_flow_leayer.csv`. Adds identity + timestamp vs balanced:

| Extra vs balanced | Columns |
| :--- | :--- |
| Flow identity | `flow id`, `protocol`, `src ip`, `dst ip`, `src port`, `dst port` |
| Timestamp | `flow start timestamp` |

**Full 119-column list**

1. flow id  
2. protocol  
3. src ip  
4. dst ip  
5. src port  
6. dst port  
7–11. flow idle time max / min / mean / std / variance  
12–16. flow active time max / min / mean / std / variance  
17–31. flow/fw/bw IAT max / min / mean / std / tot *(note: header includes duplicate `bw IAT std.1` in source CSV)*  
32–37. flow/fw/bw `iec104 packts/s` and `iec104 bytes/s`  
38–52. flow/fw/bw packet APDU length max/min/mean/std/var  
53–58. total flow/fw/bw packets; APDU total lengths  
59–60. flow duration; flow down/up ratio  
61–72. flow/fw/bw totals for IEC104 I(SeqIOA), I(SingleIOA), S, U messages  
73–83. TCP URG/PSH amounts + SYN/RST/PSH/ACK/URG/CWE/ECE counts  
84–87. fw/bw subflow packets/bytes  
88. **flow start timestamp**  
89–98. bulk avgs, init windows, TCP header lengths  
99–112. `cot=1` … `cot=13`, `cot=20`  
113–118. type_id_* (monitor/control process & system, parameter, file transfer)  
119. **Label**

---

## 2. ELEGANT — DoS / MiTM on PLCs (local)

### Local layout

```
data/elegant/IEEE_DataPort/          # original zip/tar archives
data/elegant/work_pcaps/             # unpacked cap_* files used for extraction
data/elegant/flows/                  # TRAIN-READY FLOW CSVs
  elegant_flows_all.csv              # 336,699 flows (78 cols)
  elegant_flows_balanced.csv         # 15,097 flows (undersampled DoS)
  elegant_flows_train.csv            # 80% stratified
  elegant_flows_test.csv             # 20% stratified
  <scenario>__cap_*.csv              # per-capture CSVs
```

### Extracted ML features (done)

Extractor: `scripts/extract_elegant_flows.py`  
- Parses **pcapng** via `dpkt`  
- Bidirectional IPv4 TCP/UDP flows, **30s** tumble windows for long Modbus sessions  
- Attack markers (`__ATTACK_START__/END__`, `__MiTM_ATTACK_*__`) for window labels  
- DoS one-packet floods reservoir-sampled (max ~8k flows / capture)

| Dataset file | Flows | Label mix |
| :--- | ---: | :--- |
| `elegant_flows_all.csv` | 336,699 | dos_flood 213774, dos_amp 97214, normal 25614, mitm_full_chain 50, mitm_arp 47 |
| `elegant_flows_balanced.csv` | 15,097 | 5k normal / 5k flood / 5k amp + all MiTM |
| `elegant_flows_train.csv` | 12,077 | stratified 80% |
| `elegant_flows_test.csv` | 3,020 | stratified 20% |

### Feature columns (78 total)

**CIC-style (identity):** Flow ID, Src IP, Src Port, Dst IP, Dst Port, Protocol, Timestamp  

**Volume / rate:** Flow Duration, Tot Fwd/Bwd Pkts, TotLen Fwd/Bwd, Flow Byts/s, Flow Pkts/s, Fwd/Bwd Pkts/s, Down/Up Ratio  

**Packet lengths:** Fwd/Bwd/Pkt Len Min/Max/Mean/Std/Var, Pkt Size Avg, Fwd/Bwd Seg Size Avg  

**Timing:** Flow/Fwd/Bwd IAT Mean/Std/Max/Min/Tot, Active/Idle Mean/Std/Max/Min  

**TCP flags / headers:** FIN/SYN/RST/PSH/ACK/URG/CWE/ECE counts, Fwd/Bwd PSH/URG, Fwd/Bwd Header Len, Init Fwd/Bwd Win  

**Modbus extras:** Modbus Pkts, Modbus Fn3 Count, Modbus Fn Other Count  

**Meta / label:** Scenario, SourceFile, InAttackWindow, **Label**  

**Drop before training:** `Flow ID`, `Src IP`, `Dst IP`, `Timestamp`, `Scenario`, `SourceFile` (optional keep `InAttackWindow`).

### Label classes

| Label | Meaning |
| :--- | :--- |
| `normal` | Clean Modbus/TCP (or outside attack window) |
| `dos_flood` | TCP flood toward PLC :502 |
| `dos_amp` | Amplification / volumetric toward :502 |
| `mitm_arp` | ARP poisoning only |
| `mitm_full_chain` | ARP + Modbus value rewrite |

> MiTM classes are small (~50 flows each) because those captures are short. Prefer `elegant_flows_balanced.csv` and treat MiTM as few-shot / merge to `mitm` if needed.

### Original archive inventory

```
DoS/: single_flood_rate_1/2, single_amp, multiple_flood, multiple_amp
MiTM/: MiTM_ARP_Poisoning, MiTM_Full_Chain, normal_PLC_traffic
```

Native PCAP fields and Scapy checks: `reports/elegant_feature_inventory.json`  
Flow extraction summary: `reports/elegant_flows_summary.json`

### How to re-run

```powershell
python scripts/extract_elegant_flows.py
python scripts/extract_elegant_flows.py --skip-large   # faster: normal+MiTM+flood_rate1 only
```

---

## 3. SWaT.A12 — Secure Water Treatment OT Dataset (local)

### Access & local files

| Item | Value |
| :--- | :--- |
| Version on disk | **SWaT.A12_OTDataset_Mar_26** |
| File | `data/swat/SWaT.A12_OTDataset_Mar_26/11-Mar-2026_0900_1700.csv` |
| Size | ~16.5 MB |
| Rows | **28,860** (exactly 1 Hz) |
| Time window | 2026-03-11 **09:00:00 → 17:00:59** (~8 hours) |
| Columns | **87** |
| Attack label? | **No** — this export has no `Normal/Attack` column |
| Inventory JSON | `reports/swat_feature_inventory.json` |

> This is a **newer OT historian export** (A12, Mar 2026), not the classic Dec 2015 benchmark CSV. It is richer (stage states, alarms, pump speeds) but **unlabeled for attacks**, so use **unsupervised** methods unless you get a separate attack schedule from iTrust.

### What kind of data

Process telemetry from the six-stage SWaT water-treatment testbed:

| Category | Count | Examples |
| :--- | ---: | :--- |
| Timestamp | 1 | `t_stamp` |
| Stage PLC state | 6 | `P1_STATE` … `P6_STATE` |
| Sensor process values (`.Pv`) | 31 | `LIT101.Pv`, `FIT501.Pv`, `AIT202.Pv`, `PIT501.Pv` |
| Actuator status (`.Status`) | 32 | `MV101.Status`, `P101.Status`, `UV401.Status` |
| Alarms (`.Alarm`) | 15 | `LS201.Alarm`, `LSH601.Alarm`, `PSH301.Alarm` |
| Pump speed | 2 | `P501.Speed`, `P502.Speed` |

### Naming convention

| Suffix / prefix | Meaning |
| :--- | :--- |
| `.Pv` | Process value (sensor reading) |
| `.Status` | Actuator / valve / pump state (often 0/1/2) |
| `.Alarm` | Alarm flag (`Active` / `Inactive` / sometimes `Bad Input`) |
| `.Speed` | Pump speed setpoint / reading |
| `P*_STATE` | Overall subprocess PLC state |
| FIT / LIT / AIT / PIT / DPIT | Flow / level / analyzer / pressure / ΔP |
| MV / P / UV | Motorized valve / pump / UV unit |
| LS / LSH / LSL / LSLL / PSH / PSL / DPSH | Level / pressure switch alarms |

### Full column list (87)

`t_stamp`, `P1_STATE`, `LIT101.Pv`, `FIT101.Pv`, `MV101.Status`, `P101.Status`, `P102.Status`, `P2_STATE`, `FIT201.Pv`, `AIT201.Pv`, `AIT202.Pv`, `AIT203.Pv`, `MV201.Status`, `P201.Status`–`P208.Status`, `LS201.Alarm`, `LS202.Alarm`, `LSL203.Alarm`, `LSLL203.Alarm`, `P3_STATE`, `AIT301.Pv`, `AIT302.Pv`, `AIT303.Pv`, `LIT301.Pv`, `FIT301.Pv`, `DPIT301.Pv`, `MV301`–`MV304.Status`, `P301.Status`, `P302.Status`, `PSH301.Alarm`, `DPSH301.Alarm`, `P4_STATE`, `LIT401.Pv`, `FIT401.Pv`, `AIT401.Pv`, `AIT402.Pv`, `P401`–`P404.Status`, `UV401.Status`, `LS401.Alarm`, `P5_STATE`, `FIT501`–`FIT504.Pv`, `AIT501`–`AIT504.Pv`, `PIT501`–`PIT503.Pv`, `P501.Status`, `P501.Speed`, `P502.Status`, `P502.Speed`, `MV501`–`MV504.Status`, `PSH501.Alarm`, `PSL501.Alarm`, `P6_STATE`, `LIT601.Pv`, `LIT602.Pv`, `FIT601.Pv`, `FIT602.Pv`, `P601`–`P603.Status`, `LSH601.Alarm`, `LSL601.Alarm`, `LSH602.Alarm`, `LSL602.Alarm`, `LSH603.Alarm`, `LSL603.Alarm`.

### Data-quality notes

- Some alarm columns are entirely `Bad Input` in this file (`PSH301`, `DPSH301`, `PSH501`, `PSL501`) — drop or ignore for modeling.  
- A few status/Pv fields have rare `Bad Input` strings mixed with numbers — coerce to numeric and treat as missing.  
- No nulls after load, but mixed dtypes need cleaning before ML.

### How to use for ML

| Approach | How |
| :--- | :--- |
| Unsupervised anomaly detection | Train autoencoder / Isolation Forest / PCA residual on “normal-looking” windows |
| Forecasting | Predict next-step `LIT*` / `FIT*` from history; flag large residuals |
| Supervised (only if labels arrive) | Need attack timetable from iTrust; then align to `t_stamp` |

---

## 4. Cross-dataset comparison (updated)

| Dimension | SWaT.A12 | ELEGANT | IEC-104 |
| :--- | :--- | :--- | :--- |
| Local now? | **Yes** | **Yes** | **Yes** |
| Primary data | Process OT time series | PCAP → flow CSV | Network flows + PCAP |
| Domain | Water treatment plant | PLC Modbus | Grid IEC-104 |
| Ready feature matrix | **Yes** (87 cols) | **Yes** (78 cols) | **Yes** |
| Labels | **None** in this export | 5-class | 12-class (+ `mitm_drop` pkg) |
| Best use | Process AD / forecasting | Modbus DoS/MiTM IDS | Protocol IDS / DL |

---

## 5. Next steps

1. **IEC-104:** train on balanced `tests_custom_60` / `tests_cic_60`.  
2. **ELEGANT:** train on `elegant_flows_train.csv` / evaluate on `*_test.csv`.  
3. **SWaT.A12:** clean `Bad Input`, build train/val split by time, run unsupervised process anomaly detection; ask iTrust for attack labels if supervised evaluation is needed.
