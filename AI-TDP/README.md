# AI-TDP — Hierarchical Cyber-Physical Behavior Analysis for ICS

**Source of truth** for this repository. If other docs disagree with this file, **this file wins** until it is updated.

| Item | Value |
| :--- | :--- |
| Project | AI-TDP (Industrial Control System cyber-physical behavior framework) |
| Primary dataset | **SWaT.A12** (Ensign Pre-UAT, 11 Mar 2026) |
| Framework | **PyTorch** |
| Primary metric | **Window-level anomaly detection** |
| Status | Phase 0–3 done · next: Phase 4 Network TCN |

---

## 1. Goal

Build a **research framework for cyber-physical behavior analysis** in Industrial Control Systems (ICS) — **not** another attack classifier or end-to-end IDS.

The framework answers:

> **How does the system normally behave across network, protocol, and physical domains?**

Attack / anomaly detection is a **downstream** task on learned behavior embeddings. Generating explainable IDS rules with an LLM is **future work**, not part of the current implementation.

```text
Behavior Learning → Behavior Fusion → Behavior Embedding → Deviation Detection
                                                              ↓ (future)
                                                         LLM → IDS Rules
```

---

## 2. Scientific contribution

The contribution is a **hierarchical behavior representation framework** that embeds ICS causal knowledge into the architecture:

```text
Network communication → Protocol command (CIP) → Physical process response
```

Each layer encodes its own domain and is conditioned on context from the previous layer. Detection methods (Mahalanobis, Isolation Forest) are modular and secondary.

**What this is not**

- Not a single flat model on all features
- Not direct multiclass attack classification
- Not independent per-domain anomaly scores glued together without shared behavior context

---

## 3. Dataset (source of truth for ML)

### 3.1 Primary input file

```text
data/swat/multilayer/swat_multilayer_1s.csv
```

| Property | Value |
| :--- | :--- |
| Rows | 28,860 (@ 1 Hz) |
| Columns | 256 (1 × `t_stamp` + 255 features) |
| Window | 11 Mar 2026, **09:00:00 – 17:00:59** (Asia/Singapore wall-clock) |
| Domains | Physical historian ⊕ CIP write features ⊕ ENIP network aggregates |
| Official description | First **4 hours normal**, latter **4 hours attacks** (Ensign Pre-UAT) |

**Time labels (coarse, derived — no per-row Label column in the CSV)**

| Period | Time | Role |
| :--- | :--- | :--- |
| Normal | `09:00:00` ≤ t &lt; `13:00:00` | Train behavior encoders; fit deviation detectors |
| Attack window | `13:00:00` ≤ t ≤ `17:00:59` | Evaluate window-level detection |

There is **no per-attack schedule** in-repo. Do not claim per-attack-type metrics until a schedule is added.

### 3.2 How the unified table was built

```text
Historian CSV  ─┐
CIP writes     ─┼─→  swat_multilayer_1s.csv  (join on 1-second timestamp)
Network 1s     ─┘
```

| Source | Path |
| :--- | :--- |
| Historian | `data/swat/11-Mar-2026_0900_1700.csv` |
| CIP writes (event log) | `data/swat/multilayer/cip_writes.csv` |
| Network 1s | `data/swat/multilayer/network_1s.csv` |
| Tag ↔ column map | `data/swat/multilayer/cip_tag_columns.csv` |
| PCAPs | `data/swat/SWaT.A12_PCAPs_Mar_26/` (`EnsignPreUAT_*`, ports 44818 / 2222) |

Regenerate multilayer outputs (requires `tshark`):

```powershell
cd D:\AI-TDP
python scripts/dataset/extract_swat_cip_writes.py
python scripts/dataset/extract_swat_network_1s.py
python scripts/dataset/build_swat_multilayer_dataset.py
```

See `data/swat/multilayer/README.md` for pilot / resume flags.

### 3.3 Other datasets in this repo (out of scope for the main framework)

`data/iec104/` and `data/elegant/` are separate network-IDS corpora (supervised flow CSVs). They are **not** inputs to the hierarchical SWaT behavior pipeline unless a future multi-dataset study is explicitly started. Details: `data/README.md`.

---

## 4. Feature groups (what the models actually use)

All features come from `swat_multilayer_1s.csv`. **Do not** invent CIP service codes, reads, PLC IPs, ports, or flow IAT in the main implementation — those exist only in raw PCAPs / `cip_writes.csv` and are reserved for future enrichment.

| Layer | Domain | Feature count | Columns |
| :--- | :--- | ---: | :--- |
| 1 | Network | **7** | `net_*` |
| 2 | Protocol | **162** raw → **122** after Phase 2 ZV drop | `writes_*` + `last_value_*` |
| 3 | Physical | **86** → **82** clean → **65** after Phase 2 | Historian tags |
| — | Timestamp | 1 | `t_stamp` (alignment only) |

**Modeling dims (Phase 3+):** physical **65**, protocol **122**, network **7**.

### 4.1 Network (Layer 1 — TCN)

```text
net_enip_tcp_pkts
net_enip_udp_pkts
net_total_pkts
net_total_bytes
net_unique_src_ips
net_unique_dst_ips
net_packet_rate
```

### 4.2 Protocol (Layer 2 — Transformer)

Per symbolic CIP tag:

- `writes_<TAG>` — write count in that second  
- `last_value_<TAG>` — last written integer value in that second  

**81 tags** include plant mode tags (`HMI_PLANT`, `HMI_PLANT_AUTO`, …), valves/pumps (`HMI_MV*`, `HMI_P*`), sensors (`HMI_LIT*`, `HMI_FIT*`, …), and permissives. Full map: `data/swat/multilayer/cip_tag_columns.csv`.

### 4.3 Physical (Layer 3 — GRU + cross-attention)

| Subgroup | Count | Examples |
| :--- | ---: | :--- |
| Stage states | 6 | `P1_STATE` … `P6_STATE` |
| Sensors `.Pv` | 31 | `LIT*`, `FIT*`, `AIT*`, `PIT*`, `DPIT301` |
| Actuators | 34 | `MV*.Status`, `P*.Status`, `P501/502.Speed`, `UV401.Status` |
| Alarms | 15 | `LS*`, `LSH*`, `LSL*`, `PSH*`, … |

**Drop before training (entirely `Bad Input`):**  
`PSH301.Alarm`, `DPSH301.Alarm`, `PSH501.Alarm`, `PSL501.Alarm`

Encode `Active` / `Inactive` alarms to numeric; coerce statuses as needed.

---

## 5. Architecture

### 5.1 Selected design — Hierarchical (causal)

```text
Network features  ──► [ TCN ] ──► network context
                                      │
Protocol features + network context ──► [ Transformer ] ──► protocol context
                                                                  │
Physical features + protocol context ──► [ GRU + Cross-Attention ] ──► unified embedding
                                                                              │
                                                         Mahalanobis / Isolation Forest
                                                                              │
                                                                    behavioral deviations
```

| Layer | Encoder | Input | Output |
| :--- | :--- | :--- | :--- |
| 1 Network | **TCN** | Window of 7 `net_*` features | Network behavior context |
| 2 Protocol | **Transformer encoder** | Window of **122** CIP features + L1 context | Network-aware protocol context |
| 3 Physical | **GRU + cross-attention** | Window of physical features + L2 context sequence | Unified cyber-physical embedding |

**Why these models**

- **TCN:** Stable, efficient temporal base; good gradient path through the hierarchy; sufficient for 7-D network aggregates.  
- **Transformer:** Models command-like dependencies across the protocol window; natural place to inject L1 context (token prepend or cross-attn).  
- **GRU + cross-attention:** Models continuous process dynamics; attends over the **protocol window sequence** (not a single degenerate vector) to link process change to recent CIP activity.

### 5.2 Rejected as the core (keep as baselines later)

| Approach | Role |
| :--- | :--- |
| Parallel encoders + late MLP fusion | Main **architecture** baseline (same encoders, no causal conditioning) |
| LSTM-AE / USAD / TranAD on concat features | Detection baselines |
| Isolation Forest on raw features | Non-deep baseline |

**Network LSTM-AE (supervisor baseline)** lives in the top-level [`baselines/`](baselines/) package (Pipeline 1). It does **not** replace Phase 4 TCN. Full Phase 10 concat-domain baselines (LSTM-AE / USAD / TranAD) are trained from that package. Colab: [`baselines/docs/COLAB_GUIDE.md`](baselines/docs/COLAB_GUIDE.md). `behavior/baselines/` is a compatibility shim.

### 5.3 Naming note

`data/swat/multilayer/README.md` numbers data sources as Physical / CIP / Network for **extraction order**. The **model hierarchy** always uses causal order **Network → Protocol → Physical**. Prefer model numbering in research and code.

---

## 6. Training and evaluation protocol

### 6.1 Splits (locked)

All splits are **time-contiguous**. Never random-shuffle seconds across the day.

| Split | Time range | Used for |
| :--- | :--- | :--- |
| **Train** | `09:00:00` – `11:59:59` | Fit scalers; train encoders; fit deviation head |
| **Validation** | `12:00:00` – `12:59:59` | Early stopping; select reconstruction threshold / Mahalanobis cutoff for target FPR; hyperparameter checks |
| **Test (attack)** | `13:00:00` – `17:00:59` | **Primary** window-level detection metrics |
| **Test (normal FP check)** | Same as Validation (or report Val FPR separately) | Confirm false-positive rate under normal operation |

Rationale: last morning hour is held out so validation never sees afternoon attacks, and scaler/model fitting never sees validation or test.

Windows must be **fully contained** in their assigned split. Assignment uses **both start and end** timestamps (locked rule). Boundary-straddling windows are **discarded**.

| Window start & end | Split / label |
| :--- | :--- |
| `09:00:00` ≤ start ≤ end &lt; `12:00:00` | Train / Normal |
| `12:00:00` ≤ start ≤ end &lt; `13:00:00` | Validation / Normal |
| `13:00:00` ≤ start ≤ end ≤ `17:00:59` | Test / Attack-period |
| Otherwise (straddles a boundary) | Discarded |

### 6.2 Representation objective (locked)

**Primary objective (all encoder phases): window reconstruction (MSE).**

Each domain encoder maps a window `X ∈ R^{T×F}` to an embedding `z`, then a light decoder reconstructs `X̂`. Minimize:

```text
L_recon = MSE(X̂, X)
```

| Stage | What is reconstructed | Context |
| :--- | :--- | :--- |
| Layer 1 | Network window `(T, 7)` | None |
| Layer 2 | Protocol window `(T, 122)` | L1 context available to encoder (frozen L1) |
| Layer 3 | Physical window `(T, F_phys)` | L2 protocol sequence via cross-attention (frozen L1–L2) |
| E2E fine-tune | Weighted sum `λ1 L_net + λ2 L_proto + λ3 L_phys` (default equal weights unless tuned on Val) | Full hierarchy unfrozen, small LR |

**Why reconstruction**

- Matches unsupervised **behavior learning** (model normal trajectories, not attack labels).  
- Gives a clear train/val curve for early stopping.  
- Embeddings are a by-product of explaining the window; deviation detection runs on `z`, not on raw reconstruction error (reconstruction error may be reported as an auxiliary baseline).

**Not used as the main objective (optional later ablations only):** contrastive losses, next-step-only prediction, adversarial (USAD-style) training.

### 6.3 Detection and metrics

| Rule | Detail |
| :--- | :--- |
| Framework | PyTorch |
| Fit deviation head | Unified embeddings from **Train** only |
| Threshold / hyperparams | Chosen on **Validation** (e.g. FPR ≤ 5% or best Val F1 under FPR cap) |
| Primary eval | Window-level Precision, Recall, **F1**, FPR on **Test (attack)** |
| Supporting | Score timeline vs 13:00; Val FPR; t-SNE/UMAP of embeddings |
| Optional | Point-adjusted F1; delay vs coarse 13:00 onset (not per-attack until schedule exists) |
| Default window | `T = 60` s, stride `10` (alternate strides `1` / `30` in ablations) |

### 6.4 Dual-pipeline comparison design

Two **independent** training pipelines share identical preprocessing, sliding windows, and Train / Val / Test splits. The controlled variable is the **model family** (and its native anomaly score); data and eval protocol stay fixed.

```text
Phase 3 windows (same NPZs)
        │
        ├──────────────────────┐
        ▼                      ▼
 Pipeline 1 — Baselines   Pipeline 2 — Proposed hierarchy
 LSTM-AE / USAD / TranAD   TCN → Transformer → GRU+attn → e2e
        │                      │
        └──────────┬───────────┘
                   ▼
         Shared window-level metrics
         (P / R / F1 / FPR / ROC-AUC / PR-AUC)
```

#### Shared (must not differ)

| Item | Locked source |
| :--- | :--- |
| Cleaning / EDA / feature set | Phase 1–2 selected CSV + schema |
| Scalers | Train-only RobustScaler (`behavior/outputs/scalers/`) |
| Windows | `T=60`, stride `10`, full-containment splits |
| Artifacts | `behavior/outputs/windows/{train,val,test}.npz` |
| Threshold policy | Chosen on **Validation** (e.g. FPR ≤ 5% or best Val F1 under FPR cap) |
| Primary eval | Window-level on **Test (attack)**; Val FPR reported separately |

#### Pipeline 1 — Baselines (external AD methods)

| Model | Typical input | Score used for detection |
| :--- | :--- | :--- |
| LSTM-AE | Concatenated domains `(T, 7+122+65)` (Phase 10); Network-only `(T, 7)` allowed as supervisor slice | Reconstruction error (and/or latent `z` + detector) |
| USAD | Same windows as LSTM-AE | USAD adversarial / recon score |
| TranAD | Same windows as LSTM-AE | TranAD association / recon score |

Train each on Train; early-stop / tune on Val; evaluate with the **same** metric suite as Pipeline 2. Save models, embeddings, logs, and metrics under separate baseline folders.

#### Pipeline 2 — Proposed framework (hierarchical)

1. Train **TCN** on Network `(T, 7)`.  
2. Train **Transformer** on Protocol `(T, 122)` + TCN context.  
3. Train **GRU + cross-attention** on Physical `(T, 65)` + Transformer context.  
4. **End-to-end** fine-tune (weighted multi-domain recon).  
5. Fit **Mahalanobis** (primary) and optional **Isolation Forest** on **Train** unified embeddings.  
6. Threshold on Val; evaluate on Test with the same metrics as baselines.

#### Fair-comparison notes

- Baselines and the hierarchy need **not** consume identical feature layouts at every stage: concat flat AD vs causal hierarchy is the intended contrast (§5.2 / Phase 10).  
- Map every method to one **window anomaly score**, then apply the same Val thresholding and Test metrics.  
- USAD may use its native adversarial objective; the proposed stack keeps **MSE reconstruction** (§6.2).  
- ROC-AUC / PR-AUC are supporting; primary locked metrics remain **F1 / FPR** (§6.3).  
- Phase 9 ablations (no context, parallel fusion, flat encoder, etc.) are **separate** from Pipeline 1 — they stress hierarchical design, not external methods.

#### Output layout

```text
baselines/                        ← self-contained Pipeline 1 package
├── models/ train/ eval/ notebooks/
└── outputs/
    ├── lstm_ae_net/
    ├── lstm_ae_concat/
    ├── usad_concat/
    ├── tranad_concat/
    └── evaluation/               ← comparison.md + per-model JSON

behavior/outputs/
├── windows/                      ← shared Phase 3 NPZs
├── scalers/
└── proposed/                     ← Pipeline 2 (TCN / hierarchy) when built
```

See [`baselines/README.md`](baselines/README.md) and [`baselines/docs/COLAB_GUIDE.md`](baselines/docs/COLAB_GUIDE.md).

---

## 7. Repository layout

```text
AI-TDP/
├── README.md                 ← this file (source of truth)
├── data/                     ← datasets (swat / elegant / iec104)
├── scripts/
│   ├── dataset/              ← PCAP/historian extraction & multilayer build
│   ├── phases/               ← Phase 1–3 runners
│   └── shims/                ← thin wrappers (e.g. network LSTM-AE)
├── reports/
│   ├── docs/                 ← training explainer, bibliography, feature docs
│   ├── swat/                 ← cleaning / EDA / phase summaries (+ eda/)
│   ├── elegant/ · iec104/    ← other dataset inventories
│   └── diagrams/
├── notebooks/
│   └── legacy/               ← old Colab packs (active notebooks → baselines/)
├── baselines/                ← Pipeline 1 (flat AD + experimental cascade)
│   ├── docs/                 ← Colab guides
│   ├── notebooks/ · models/ · train/ · eval/ · detect/
│   └── outputs/
└── behavior/                 ← Pipeline 2 (proposed hierarchy) + Phase 1–3 data code
    ├── data/                 ← cleaning, EDA, windows, datasets, splits
    └── outputs/              ← windows/, scalers/, schemas
```

---

## 8. Implementation roadmap (phases)

Implement **in order**. Do not skip cleaning/EDA or jump to detection without validated intermediate embeddings.

### Phase 0 — Dataset ready ✅

- [x] Historian CSV available  
- [x] CIP writes extracted from PCAPs  
- [x] Network 1s summaries extracted  
- [x] `swat_multilayer_1s.csv` built and verified  

**Exit criterion:** Unified CSV exists with network + protocol + physical columns aligned on `t_stamp`.

---

### Phase 1 — Data cleaning ✅

**Goal:** Deterministic, documented cleaned table with no silent bad values.

- [x] Load `swat_multilayer_1s.csv`; parse `t_stamp`
- [x] Partition network / protocol / physical columns
- [x] Drop always-bad alarms (`PSH301`, `DPSH301`, `PSH501`, `PSL501`)
- [x] Encode remaining alarms; coerce Status/Speed/STATE; handle historian `Bad Input`
- [x] Protocol `writes_*` / `last_value_*` fill rules
- [x] Network coverage check / fill
- [x] Cleaning report + schema

**Outputs**

| Artifact | Path |
| :--- | :--- |
| Cleaned table | `data/swat/multilayer/swat_multilayer_1s_clean.csv` (28860 × 252) |
| Feature schema | `behavior/outputs/feature_schema.json` |
| Report | `reports/swat/swat_cleaning_report.md` / `.json` |
| Code | `behavior/data/columns.py`, `behavior/data/cleaning.py` |
| CLI | `python scripts/phases/run_phase1_cleaning.py` |

**Exit criterion:** One clean feature matrix with fixed column lists and a reproducible cleaning report. **Met** (82 physical + 162 protocol + 7 network = 251 features).

---

### Phase 2 — Exploratory data analysis (EDA) ✅

**Goal:** Understand normal vs attack-period behavior **before** modeling; inform scaling and window choices.

- [x] Variance analysis: full-day vs Train (`09:00–12:00`)
- [x] Drop **full-day** zero-variance features only; keep train-silent / attack-active
- [x] Morning vs afternoon distributions + timelines (no IQR/Z-score outlier removal)
- [x] Train-only correlation heatmaps per domain
- [x] Protocol write sparsity; confirm `log1p(writes_*)` for Phase 3
- [x] Selected schema + CSV for Phase 3

**Variance policy**

| Rule | Action |
| :--- | :--- |
| Full-day variance ≈ 0 | Drop in Phase 2 |
| Train variance ≈ 0 but full-day &gt; 0 | **Keep** (may activate in attack window) |
| Statistical outliers | **Never** remove via IQR/Z-score |
| Phase 1 role | Cleaning only (4 locked alarms); ZV report + drop owned by Phase 2 |

**Outputs**

| Artifact | Path |
| :--- | :--- |
| Selected table | `data/swat/multilayer/swat_multilayer_1s_selected.csv` (28860 × 195) |
| Selected schema | `behavior/outputs/feature_schema_selected.json` |
| EDA summary | `reports/swat/swat_eda_summary.md` / `.json` |
| Figures | `reports/swat/eda/*.png` |
| CLI | `python scripts/phases/run_phase2_eda.py` |

**Result:** 251 → **194** features (57 full-day constants dropped; 107 train-silent/attack-active kept). `log1p(writes_*)=true`; window defaults `T=60`, stride=`10`.

---

### Phase 3 — Windows, scaling, and validation split ✅

**Goal:** Reproducible PyTorch-ready tensors with the locked split (§6.1).

- [x] `log1p` on `writes_*`
- [x] RobustScaler per domain, fit on Train seconds only (`n_fit_rows=10800`)
- [x] Windows `T=60`, stride=`10` (2871 kept; 10 boundary straddlers discarded)
- [x] Split by full containment (start+end); leakage checks passed
- [x] `SwatWindowDataset` + DataLoader smoke test

**Window counts**

| Split | N | start → end range |
| :--- | ---: | :--- |
| Train | 1075 | 09:00:00 – 11:59:59 |
| Val | 355 | 12:00:00 – 12:59:59 |
| Test | 1441 | 13:00:00 – 17:00:59 |

**Outputs**

| Artifact | Path |
| :--- | :--- |
| Config | `behavior/outputs/config_windows.json` |
| Scalers | `behavior/outputs/scalers/{physical,protocol,network}.joblib` |
| Windows | `behavior/outputs/windows/{train,val,test}.npz` + `meta.json` |
| Dataset | `behavior/data/dataset.py` (`SwatWindowDataset`) |
| Report | `reports/swat/swat_phase3_windows_summary.md` |
| CLI | `python scripts/phases/run_phase3_windows.py` |

**Shapes:** `(N, 60, 7)` net · `(N, 60, 122)` proto · `(N, 60, 65)` phys

---

### Phase 4 — Layer 1: Network TCN

**Goal:** Standalone network behavior encoder.

**Input:** `behavior/outputs/windows/*.npz` via `SwatWindowDataset` / `make_loader`.

Tasks:

1. Implement TCN on `(B, T, 7)` + decoder for reconstruction.  
2. Train with **`L_recon` (MSE)** on Train; early-stop on Val reconstruction.  
3. Export embeddings for Train / Val / Test.  
4. Supporting viz: t-SNE/UMAP of embeddings (morning vs afternoon).  

**Deliverables:** `behavior/models/tcn.py`, checkpoint, embedding export.

**Exit criterion:** Val reconstruction converges; no Test labels in training loss.

#### Parallel baseline — Network LSTM-AE (does not replace TCN)

Supervisor slice + full Pipeline 1 baselines live in top-level **`baselines/`**.

| Item | Path |
| :--- | :--- |
| Package | [`baselines/`](baselines/) |
| Models | `baselines/models/{lstm_ae,usad,tranad}.py` |
| Train | `python -m baselines.train.train_lstm_ae` (also `train_usad`, `train_tranad`) |
| Eval | `python -m baselines.eval.run_eval` |
| Colab | [`baselines/docs/COLAB_GUIDE.md`](baselines/docs/COLAB_GUIDE.md) |
| Outputs | `baselines/outputs/` |

`behavior/baselines/` remains a thin import shim for older scripts.

---

### Phase 5 — Layer 2: Protocol Transformer (freeze L1)

**Goal:** Network-aware protocol behavior.

Tasks:

1. Freeze Layer 1.  
2. Transformer on `(B, T, 122)` with L1 context; decode protocol window; **`L_recon`**.  
3. Train on Train; early-stop on Val.  
4. Quick check: Val loss with vs without L1 context (feeds Phase 9 ablations).  

**Deliverables:** `behavior/models/protocol_transformer.py`, checkpoint.

**Exit criterion:** Layer 2 trains with frozen L1; context path tested.

---

### Phase 6 — Layer 3: Physical GRU + cross-attention (freeze L1–L2)

**Goal:** Unified cyber-physical embedding.

Tasks:

1. Freeze Layers 1–2.  
2. GRU over physical window; cross-attend to **protocol sequence**; reconstruct physical window.  
3. Train / early-stop on Val `L_recon`.  
4. Export unified embeddings.  

**Deliverables:** `behavior/models/physical_gru.py`, `behavior/models/hierarchy.py`, checkpoint.

**Exit criterion:** Forward pass Network→Protocol→Physical yields one `z` per window.

---

### Phase 7 — End-to-end fine-tune

**Goal:** Light joint adaptation of the full hierarchy.

Tasks:

1. Unfreeze all layers; small LR.  
2. Optimize weighted multi-domain reconstruction (§6.2) on Train; early-stop on Val.  
3. Save final hierarchy checkpoint.  

**Exit criterion:** Val multi-loss improves or matches Phase 6 without representation collapse.

---

### Phase 8 — Deviation detection + window-level evaluation

**Goal:** Primary research metric.

Tasks:

1. Fit **Mahalanobis** (primary) on **Train** unified embeddings; optionally **Isolation Forest**.  
2. Choose threshold on **Validation** under FPR constraint.  
3. Score Test (attack) windows; report Precision / Recall / **F1** / FPR.  
4. Report Val FPR; plot scores vs 13:00.  
5. Optional auxiliary: detection from Layer-3 reconstruction error alone (for comparison).  

**Deliverables:** `behavior/detect/`, `behavior/eval/`, metrics + figures.

**Exit criterion:** One command reproduces window-level metrics from the frozen config.

---

### Phase 9 — Ablation experiments

**Goal:** Show that hierarchical conditioning and design choices matter — not only a single lucky run.

Run on the **same** windows, scalers, and metrics as Phase 8.

| ID | Ablation | What changes | What stays fixed |
| :--- | :--- | :--- | :--- |
| A1 | **No L1→L2 context** | Protocol Transformer without network context | L1/L3 modules, detection |
| A2 | **No L2→L3 context** | Physical GRU without cross-attention to protocol | L1/L2, detection |
| A3 | **Parallel late fusion** | Three encoders independent; concat `z` → deviation | Same encoders where possible |
| A4 | **Single flat encoder** | One TCN or Transformer on all features | Window config, detection |
| A5 | **Detection head** | IF only vs Mahalanobis only vs recon-error only | Frozen hierarchy embeddings |
| A6 | **Window sensitivity** | `T ∈ {30, 60, 120}`, stride ∈ `{10, 30}` | Best architecture from main run |
| A7 | **Layer drop** | Detect from L1-only / L2-only / L3-only embeddings | Per-layer checkpoints |

Optional stretch (not required for first paper/report): swap L3 GRU→Mamba, L1 TCN→TimesNet/PatchTST.

**Deliverables:** `behavior/ablations/`, comparison table in `reports/swat/swat_ablation_results.md`.

**Exit criterion:** Table shows hierarchical model vs A1–A3 (minimum) on Test F1/FPR.

---

### Phase 10 — Baselines (external methods)

**Goal:** Compare against standard AD pipelines (distinct from architecture ablations).

Implemented in top-level [`baselines/`](baselines/) (same Phase 3 windows):

1. LSTM-AE (`net` supervisor slice + `concat` domains)  
2. USAD (concat)  
3. TranAD (concat)  
4. Shared eval: Val FPR + Test detection rate + ROC/PR on Val∪Test  

**CLI:** see [`baselines/README.md`](baselines/README.md). **Colab:** [`baselines/docs/COLAB_GUIDE.md`](baselines/docs/COLAB_GUIDE.md).

**Exit criterion:** Comparison table hierarchical vs external baselines, same Test windows.

---

### Phase 11 — Structured behavioral events (optional stretch)

Convert deviations into structured records (time, layer attribution, top features) for later LLM use. **No LLM in this phase.**

---

### Phase 12 — Future work (out of current scope)

- Enrich protocol from `cip_writes.csv` (service codes, reads, IPs).  
- Enrich network from PCAPs (flows, ports, IAT).  
- Per-attack schedule labels and per-attack metrics.  
- LLM → explainable IDS rules.  
- Digital twin / custom attack traffic generation.  
- Modern encoder swaps beyond Phase 9 stretch.

---

## 9. Training principles (do not violate)

1. **Clean → EDA → windows** before any encoder training.  
2. **Normal-only Train** for scalers, encoders, and deviation-head fit.  
3. **Validation** (`12:00–13:00`) for early stopping and thresholding — never for fitting scalers/covariance.  
4. **Representation objective = window reconstruction (MSE)** unless an ablation explicitly changes it.  
5. **Layer-wise pretrain → freeze → next layer → e2e fine-tune.**  
6. **Time-based splits** — no random shuffle across the day.  
7. **Protocol = 122 selected columns** (after Phase 2 ZV drop; started from 162).  
8. **Primary metric = window-level F1/FPR** on the attack Test period.  
9. **Ablations (Phase 9)** required before claiming hierarchical benefit.

---

## 10. Related documents

| Doc | Role |
| :--- | :--- |
| `README.md` (this file) | **Source of truth** |
| `baselines/` | Pipeline 1 package (models, train, eval, Colab) |
| `baselines/docs/COLAB_GUIDE.md` | Colab how-to for baselines (ops only; not SoT) |
| `notebooks/README.md` | Pointer → `baselines/notebooks/` (legacy under `notebooks/legacy/`) |
| `data/README.md` | All local datasets and which files to open |
| `data/swat/multilayer/README.md` | Multilayer extract/merge how-to |
| `reports/docs/TRAINING_EXPLAINER.md` | Plain-language training story (broader than SWaT hierarchy) |
| `reports/docs/PROFESSIONAL_DATASET_DOCUMENTATION.md` | Architecture / devices / protocols |
| `reports/docs/DATASET_FEATURE_REPORT.md` | Feature inventories across datasets |
| `ReportModel-AbdulRehman.pdf` | Model-selection internship report (align claims with this README) |

---

## 11. Quick start (current)

```powershell
cd D:\AI-TDP
python scripts/phases/run_phase1_cleaning.py
python scripts/phases/run_phase2_eda.py
python scripts/phases/run_phase3_windows.py
```

| Stage | Path |
| :--- | :--- |
| Raw unified | `data/swat/multilayer/swat_multilayer_1s.csv` |
| Cleaned | `data/swat/multilayer/swat_multilayer_1s_clean.csv` |
| Selected (EDA) | `data/swat/multilayer/swat_multilayer_1s_selected.csv` |
| **Phase 4 input** | `behavior/outputs/windows/{train,val,test}.npz` |

**Next:** Phase 4 — Network TCN on `(B, 60, 7)`.

---

## 12. Decision log (locked)

| Decision | Choice | Date |
| :--- | :--- | :--- |
| Core problem | Behavior representation learning | 2026-07 |
| Architecture | Hierarchical Network → Protocol → Physical | 2026-07 |
| Models | TCN / Transformer / GRU+cross-attn | 2026-07 |
| Detection | Mahalanobis (+ optional IF), post-embedding | 2026-07 |
| Dataset | SWaT.A12 multilayer 1s CSV | 2026-07 |
| Protocol features | 162 columns from unified CSV; **122 after Phase 2** | 2026-08-03 |
| Primary metric | Window-level anomaly detection | 2026-08-03 |
| ML framework | PyTorch | 2026-08-03 |
| LLM / rich CIP / digital twin | Future work | 2026-08-03 |
| Data cleaning | Explicit Phase 1 before EDA/modeling | 2026-08-03 |
| EDA | Explicit Phase 2 before windows | 2026-08-03 |
| Validation split | `12:00–13:00` morning holdout; Train `09:00–12:00`; Test `13:00–17:00` | 2026-08-03 |
| Window assignment | Fully contained (start+end); discard straddlers | 2026-08-03 |
| Representation objective | Per-domain **window reconstruction (MSE)**; e2e weighted sum | 2026-08-03 |
| Ablations | Required Phase 9 (context off, parallel, flat, detector, window, layer-drop) | 2026-08-03 |
| Zero-variance | Report full-day + Train; **drop full-day only** in Phase 2; keep attack-active | 2026-08-03 |
| Outlier removal | Forbidden (IQR/Z-score); ICS spikes may be attacks | 2026-08-03 |
| log1p writes | Enabled for Phase 3 (EDA sparsity) | 2026-08-03 |
| Scaler | RobustScaler per domain, Train seconds only | 2026-08-03 |
| Windows | T=60, stride=10 → train 1075 / val 355 / test 1441 (10 discarded) | 2026-08-03 |
| Dual-pipeline comparison | Shared Phase 3 windows/splits/metrics; Pipeline 1 = LSTM-AE/USAD/TranAD; Pipeline 2 = hierarchy + Mahalanobis | 2026-08-03 |
| Baselines package | Top-level `baselines/` (models, train, eval, Colab); `behavior/baselines/` shim | 2026-08-04 |

Update this table when a decision changes.
