# Internship Projects

This repository contains internship project source code for **OTX**, **OTX2**, and **AI-TDP**.

## Repository Structure

| Project | Folder | Description |
| :--- | :--- | :--- |
| OTX | [`OTX/`](./OTX) | OTX integration (backend + frontend) |
| OTX2 | [`OTX2/`](./OTX2) | Alternative OTX integration (backend + frontend) |
| AI-TDP | [`AI-TDP/`](./AI-TDP) | ICS cyber-physical behavior learning → IDS rule generation (SWaT.A12) |

## Setup Instructions

Refer to each project's README:

- [OTX README](./OTX/README.md)
- [OTX2 README](./OTX2/README.md)
- [AI-TDP README](./AI-TDP/README.md) — **source of truth** for the behavior-learning framework

### AI-TDP quick start

```powershell
cd AI-TDP
pip install -r requirements.txt
python scripts/phases/run_phase1_cleaning.py
python scripts/phases/run_phase2_eda.py
python scripts/phases/run_phase3_windows.py
python -m baselines.train.train_lstm_ae --mode net --epochs 50
```

Large datasets (CSV/PCAP) are not in Git — see [`AI-TDP/data/DOWNLOAD_STATUS.md`](./AI-TDP/data/DOWNLOAD_STATUS.md).
