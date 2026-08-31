# How We Use These Datasets (Training Explainer)

A plain-language guide you can use to explain the project to someone else:  
**what the data is, what we use it for, and how training works.**

---

## 1. The story in one minute

Industrial plants talk over special network protocols (like **Modbus** on PLCs, or **IEC 60870-5-104** in power/telecontrol). Attackers can flood those links, inject bad commands, or sit in the middle and change values.

We have **recorded traffic from lab testbeds**, already turned into **tables of numbers (features)**.  
Each **row = one network “flow”** (a conversation summary).  
Each **column = a feature** (how long it lasted, how many packets, rates, flags, protocol counts…).  
One column is the **Label** (normal vs which attack).

We train a machine-learning model to **predict the Label from the other columns**.

```
Traffic capture (PCAP)
        │
        ▼
Feature table (CSV)     ← this is what we train on
        │
        ▼
Classifier model        ← learns patterns of “normal” vs “attack”
        │
        ▼
Prediction on new flows ← IDS-style detection
```

---

## 2. What we have locally (two usable datasets)

| Dataset | Domain | Protocol | Question the model answers |
| :--- | :--- | :--- | :--- |
| **IEC 60870-5-104** | Electric / telecontrol style | IEC-104 over TCP | Is this flow normal, or a specific bad command / DoS / (extra) MiTM drop? |
| **ELEGANT** | PLC / Modbus water-level sim | Modbus/TCP | Is this flow normal, DoS flood, DoS amp, ARP MiTM, or full-chain MiTM? |
| **SWaT.A12** | Water treatment plant | Process OT historian | Detect abnormal plant behaviour (levels, flows, actuators) — **unsupervised** (no attack label in this export) |

**Different jobs:**

- **IEC-104 / ELEGANT** → *network intrusion detection* (detect bad traffic).  
- **SWaT.A12** → *process anomaly detection* (detect weird plant behaviour even if you have no packet labels).

You can tell a teammate:  
*“We are not training on raw wire dumps for the first models. We train on feature CSVs that summarize each flow.”*

---

## 3. Which files we actually use

Full folder map: [`data/README.md`](../data/README.md).

### IEC-104 — start here

```
data/iec104/balanced/.../iec104_train_test_csvs/
  tests_custom_60/train_60_custom_script.csv   ← TRAIN
  tests_custom_60/test_60_custom_script.csv    ← TEST
```

- **custom** = features that understand IEC-104 (APDU sizes, COT, TypeID…). Best for *protocol abuse*.  
- **cic** (same folder tree, `tests_cic_60`) = generic TCP/IP stats. Best for *generic flood / volume* behaviour.

Already **balanced** and **pre-split** into train/test.

### ELEGANT — start here

```
data/elegant/flows/elegant_flows_train.csv   ← TRAIN
data/elegant/flows/elegant_flows_test.csv    ← TEST
```

Built from PCAPs (30 s windows + Modbus counters + attack-marker labels).

**Note for explanations:** MiTM labels are rare (~50 flows). Either merge `mitm_arp` + `mitm_full_chain` into one `mitm` class, or treat MiTM as a stretch goal.

### SWaT.A12 — start here

```
data/swat/SWaT.A12_OTDataset_Mar_26/11-Mar-2026_0900_1700.csv
```

- **28,860** rows @ 1 Hz, **87** OT columns (sensors `.Pv`, actuators `.Status`, alarms, stage states).  
- **No `Normal/Attack` label** → use unsupervised anomaly detection or forecasting, not multiclass IDS.  
- Split by **time** (e.g. first 6 hours train, last 2 hours test), not randomly — this is a time series.

---

## 4. What “features” mean (explainable example)

Imagine one row:

| Flow Duration | Flow Pkts/s | SYN Flag Cnt | Modbus Fn3 Count | Label |
| ---: | ---: | ---: | ---: | :--- |
| 0.002 | 5000 | 1 | 0 | dos_flood |
| 30.0 | 25 | 0 | 120 | normal |

- The **flood** row is short, huge rate, almost no real Modbus reads.  
- The **normal** row is a steady polling conversation (function code 3 = read holding registers).

The model learns those differences across **dozens of columns**, not just one.

**Columns to drop before training** (they identify devices, not attack physics):

- `Flow ID`, `Src IP`, `Dst IP`, `Timestamp`  
- For ELEGANT also: `Scenario`, `SourceFile`  
- Keep `Label` as the target **y**. Everything else usable is **X**.

---

## 5. How training works (step by step)

You can walk someone through this recipe for **either** dataset.

### Step A — Load

```python
import pandas as pd

train = pd.read_csv("data/elegant/flows/elegant_flows_train.csv")
test  = pd.read_csv("data/elegant/flows/elegant_flows_test.csv")

y_train = train["Label"]
y_test  = test["Label"]
```

### Step B — Build X (features only)

```python
drop = ["Flow ID", "Src IP", "Dst IP", "Timestamp",
        "Scenario", "SourceFile", "Label"]  # Label is target
# For IEC-104 custom files, drop may only be ["Label"] plus any IP-like fields if present

X_train = train.drop(columns=[c for c in drop if c in train.columns], errors="ignore")
X_test  = test.drop(columns=[c for c in drop if c in test.columns], errors="ignore")
```

### Step C — Clean

```python
X_train = X_train.replace([float("inf"), float("-inf")], pd.NA).fillna(0)
X_test  = X_test.replace([float("inf"), float("-inf")], pd.NA).fillna(0)
```

### Step D — Train a first model (example: Random Forest)

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

clf = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",  # helps rare MiTM / minority classes
    random_state=42,
    n_jobs=-1,
)
clf.fit(X_train, y_train)
pred = clf.predict(X_test)

print(classification_report(y_test, pred))
print(confusion_matrix(y_test, pred))
```

### Step E — What “good” looks like

- High **precision**: when we say “attack”, we’re usually right (few false alarms).  
- High **recall**: we catch most real attacks (few misses).  
- Watch the **confusion matrix**: which attacks look like each other.

For a demo pitch:  
*“We train a classifier on labeled industrial flows. On a held-out test set, we measure precision/recall per attack type.”*

---

## 6. Suggested experiment plan (what → what)

| Priority | Dataset | Model goal | Why |
| :--- | :--- | :--- | :--- |
| 1 | IEC-104 `tests_custom_60` | Multiclass IDS (12 labels) | Cleanest ready-made industrial protocol set |
| 2 | ELEGANT train/test | Multiclass Modbus IDS (5 labels) | Real PLC DoS/MiTM story |
| 3 | SWaT.A12 OT CSV | Unsupervised process AD | Physical plant story; different modality |
| 4 | IEC-104 `tests_cic_60` | Compare vs custom features | Shows value of protocol-aware features |

**Do not mix IEC-104, ELEGANT, and SWaT rows into one table** without a careful redesign: different modalities (network vs process), different feature columns, different label sets.

---

## 7. How to explain the directory to a non-ML person

> “`data/` holds the datasets.  
> For each one we keep original downloads for reproducibility, but we **train only on CSV feature tables**.  
> IEC-104 already came with those tables under `balanced/`.  
> ELEGANT came as PCAP archives; we converted them into `elegant/flows/`.  
> `reports/` has the feature inventory Word doc.  
> `scripts/` has the tools that built the CSVs and the report.”

Point them at:

1. `data/README.md` — map of folders  
2. `reports/Local_Dataset_Feature_Inventory.docx` — feature lists  
3. This file — training story  

---

## 8. Common questions you might get

**Q: Why not train on PCAPs directly?**  
A: Models need fixed-length numeric vectors. Flows compress thousands of packets into one trainable row.

**Q: Why so many folders under ELEGANT?**  
A: Download → unpack → extract features. Only `flows/` matters for training.

**Q: Why is MiTM accuracy maybe weak?**  
A: Few MiTM samples. Need more data, class merge, or anomaly detection focused on Modbus value changes.

**Q: Binary (attack vs normal) or multiclass?**  
A: Both valid. Multiclass is richer; binary is easier and often higher scores. Start multiclass on IEC-104; optionally collapse to binary for a dashboard demo.

**Q: Deep learning?**  
A: Tabular random forests / XGBoost are strong baselines here. Try neural nets after the baseline is solid.

---

## 9. One-slide summary (copy/paste)

- **Data:** Labeled industrial network flows (IEC-104 + Modbus/ELEGANT).  
- **Input X:** Flow statistics (rates, sizes, flags, protocol counters).  
- **Output y:** Attack class or normal.  
- **Train files:** `iec104/.../tests_custom_60/train_*.csv` and `elegant/flows/elegant_flows_train.csv`.  
- **Method:** Supervised classification → evaluate on held-out test CSV.  
- **Outcome:** A prototype industrial IDS model for those protocols.

---

## 10. Minimal “hello ML” command chain

```powershell
cd C:\Users\PMYLS\Desktop\AI-TDP
python -c "import pandas as pd; from sklearn.ensemble import RandomForestClassifier; from sklearn.metrics import classification_report; tr=pd.read_csv('data/elegant/flows/elegant_flows_train.csv'); te=pd.read_csv('data/elegant/flows/elegant_flows_test.csv'); drop=['Flow ID','Src IP','Dst IP','Timestamp','Scenario','SourceFile','Label']; Xtr=tr.drop(columns=[c for c in drop if c in tr.columns]).fillna(0); Xte=te.drop(columns=[c for c in drop if c in te.columns]).fillna(0); clf=RandomForestClassifier(n_estimators=100,class_weight='balanced',random_state=42,n_jobs=-1).fit(Xtr,tr['Label']); print(classification_report(te['Label'], clf.predict(Xte)))"
```

(Same idea for IEC-104 custom train/test paths.)
