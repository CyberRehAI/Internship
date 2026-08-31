# Dataset Download Status

Large dataset files are **not** stored in Git. Regenerate or download them locally.

## SWaT.A12 (primary)

| Artifact | Path | How to obtain |
| :--- | :--- | :--- |
| Historian CSV | `data/swat/11-Mar-2026_0900_1700.csv` | From iTrust / Ensign Pre-UAT package |
| PCAPs | `data/swat/SWaT.A12_PCAPs_Mar_26/` | Same package |
| Multilayer table | `data/swat/multilayer/swat_multilayer_1s.csv` | Run extraction scripts (see root `README.md` §3.2) |

```powershell
cd AI-TDP
python scripts/dataset/extract_swat_cip_writes.py
python scripts/dataset/extract_swat_network_1s.py
python scripts/dataset/build_swat_multilayer_dataset.py
```

## Optional corpora (out of main pipeline scope)

- `data/iec104/` — IEC-60870-5-104 flow CSVs  
- `data/elegant/` — ELEGANT Modbus DoS/MiTM flows  

See [`data/README.md`](README.md) for details.
