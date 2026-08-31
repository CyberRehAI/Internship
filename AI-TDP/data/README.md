# Data Directory Guide

What each folder is for, and **which files to open for training**.

```
data/
├── iec104/              # IEC 60870-5-104 (grid / telecontrol traffic)
├── elegant/             # ELEGANT PLC Modbus DoS + MiTM
├── swat/                # SWaT.A12 OT process historian
└── DOWNLOAD_STATUS.md   # What’s downloaded vs still blocked
```

---

## Mental model (read this first)

| Stage | What it is | Example |
| :--- | :--- | :--- |
| **1. Raw download** | Archives / official packages | `elegant/IEEE_DataPort/*.zip` |
| **2. Unpacked packets** | PCAP / PCAPNG captures | `elegant/work_pcaps/`, `iec104/.../*.pcap` |
| **3. Feature tables** | Rows = flows/samples, columns = features | `elegant/flows/*.csv`, `iec104/balanced/**/*.csv` |

**For machine learning you almost always use stage 3 only.**

```
Raw PCAP  -->  Feature extraction  -->  CSV table  -->  Train model
```

IEC-104 already included stage-3 CSVs.  
ELEGANT PCAPs were converted into stage-3 CSVs under `elegant/flows/`.  
SWaT.A12 is already a stage-3 OT historian CSV (process values, not network flows).

---

## 1. IEC-104 — `data/iec104/`

### Use these for training (recommended)

```
iec104/balanced/Balanced_IEC104_Train_Test_CSV_Files/iec104_train_test_csvs/
├── tests_cic_60/      ← generic TCP/IP flow features (84 columns)
│   ├── train_60_CICIFlow.csv
│   └── test_60_CICIFlow.csv
└── tests_custom_60/   ← IEC-104 protocol-aware features (112 columns)
    ├── train_60_custom_script.csv
    └── test_60_custom_script.csv
```

Other timeout folders (`15`, `30`, `90`, `120`, `180`) are the same idea with different flow-timeout settings. **60 seconds is a good default.**

| If you want… | Prefer |
| :--- | :--- |
| Generic network IDS (ports, rates, flags) | `tests_cic_*` |
| Detect bad IEC-104 commands / DoS of ASDUs | `tests_custom_*` |

### What the other folders are

| Path | Role |
| :--- | :--- |
| `20200425_..._m_sp_na_1_DoS/` | One attack day, split **per device** (iecserver1–7, qtester) |
| `20200605_..._c_rd_na_1/` | Unauthorized read attack + attackers’ captures |
| `20200608_..._mitm_drop/` | MITM packet-drop (CIC CSVs only) |
| `ReadMe.pdf` | Official documentation |

Each device folder usually contains:

- `*.pcap` — raw traffic  
- `*.pcap_Flow.csv` — CIC features  
- `*iec104_network_flow*.csv` — custom IEC-104 features  

You **don’t need** these for a first ML demo if you use `balanced/`.

---

## 2. ELEGANT — `data/elegant/`

### Use these for training (recommended)

```
elegant/flows/
├── elegant_flows_train.csv      ← train here
├── elegant_flows_test.csv       ← evaluate here
├── elegant_flows_balanced.csv   ← balanced full set
└── elegant_flows_all.csv        ← everything (large / imbalanced)
```

| File | When to use |
| :--- | :--- |
| `elegant_flows_train.csv` | Fit the model |
| `elegant_flows_test.csv` | Measure accuracy / F1 |
| `elegant_flows_balanced.csv` | Exploratory analysis |
| `elegant_flows_all.csv` | Only if you want maximum DoS volume |
| `dos_flood__cap_....csv` etc. | Intermediate per-capture pieces — usually ignore |

### What the other folders are

| Path | Role | Open for training? |
| :--- | :--- | :--- |
| `IEEE_DataPort/DoS/` | Original zip/tar downloads | No |
| `IEEE_DataPort/MiTM/` | Original MiTM / normal archives | No |
| `work_pcaps/` | Unpacked `cap_*` used by the extractor | No |
| `extracted/` | Early sample captures | No |

Re-extract flows (if needed):

```powershell
python scripts/dataset/extract_elegant_flows.py
```

---

## 3. SWaT — `data/swat/`

### Use this for process ML (recommended)

```
swat/11-Mar-2026_0900_1700.csv
```

| Property | Value |
| :--- | :--- |
| Version | SWaT.A12 OT Dataset (Mar 2026) |
| Rows | 28,860 @ 1 Hz (~8 hours: 09:00–17:00 on 11-Mar-2026) |
| Columns | 87 (timestamp + stage states + sensors + actuators + alarms + speeds) |
| Attack labels | **None** in this file |

| If you want… | Approach |
| :--- | :--- |
| Detect weird plant behaviour | Unsupervised anomaly detection / forecasting residuals |
| Supervised attack detection | Need a separate attack schedule from iTrust (not in this CSV) |
| Cyber-physical multi-layer profiling | `swat/multilayer/swat_multilayer_1s.csv` (see below) |

**Drop / clean before modeling:** columns that are entirely `Bad Input` (`PSH301.Alarm`, `DPSH301.Alarm`, `PSH501.Alarm`, `PSL501.Alarm`), and coerce mixed string statuses to numbers.

### Multi-layer dataset (physical + CIP control + network)

PCAPs under `swat/SWaT.A12_PCAPs_Mar_26/` are **EtherNet/IP (CIP)** (ports 44818 / 2222), not Modbus. Pipeline:

```
python scripts/dataset/extract_swat_cip_writes.py
python scripts/dataset/extract_swat_network_1s.py
python scripts/dataset/build_swat_multilayer_dataset.py
```

Outputs in `swat/multilayer/`:

| File | Role |
| :--- | :--- |
| `cip_writes.csv` | CIP Write Tag requests (symbolic tags kept as-is) |
| `network_1s.csv` | Per-second ENIP TCP/UDP summaries |
| `swat_multilayer_1s.csv` | Historian ⊕ CIP writes ⊕ network @ 1 Hz |
| `cip_tag_columns.csv` | Tag name ↔ feature column map |

CIP tags are **independent control features** (no forced map onto historian variables). Details: [`swat/multilayer/README.md`](swat/multilayer/README.md).

---

## Quick “open this file” cheat sheet

| Goal | Open this |
| :--- | :--- |
| Train IEC-104 classifier (start) | `iec104/balanced/.../tests_custom_60/train_60_custom_script.csv` |
| Test IEC-104 classifier | same folder `test_60_custom_script.csv` |
| Train PLC/Modbus DoS–MiTM model | `elegant/flows/elegant_flows_train.csv` |
| Test that model | `elegant/flows/elegant_flows_test.csv` |
| Process anomaly detection (SWaT) | `swat/11-Mar-2026_0900_1700.csv` |
| Cyber-physical multi-layer (SWaT) | `swat/multilayer/swat_multilayer_1s.csv` |
| Share feature documentation | `reports/docs/Local_Dataset_Feature_Inventory.docx` |

For **how** to train and how to explain the story to someone else, see:

→ [`../reports/docs/TRAINING_EXPLAINER.md`](../reports/docs/TRAINING_EXPLAINER.md)

For **architecture, devices, protocols, and diagrams**, see:

→ [`../reports/docs/PROFESSIONAL_DATASET_DOCUMENTATION.md`](../reports/docs/PROFESSIONAL_DATASET_DOCUMENTATION.md)  
→ [`../reports/diagrams/`](../reports/diagrams/)
