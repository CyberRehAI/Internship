# SWaT.A12 Multi-Layer Dataset

Unified **1-second** cyber-physical table for profiling:

| Layer | File | Content |
| :--- | :--- | :--- |
| L1 Physical | (merged from) `../11-Mar-2026_0900_1700.csv` | Process / actuator / alarm tags |
| L2 Control | `cip_writes.csv` | CIP Write Tag requests (symbolic tags as-is) |
| L3 Network | `network_1s.csv` | EtherNet/IP TCP/UDP 1s summaries |
| **Merged** | `swat_multilayer_1s.csv` | All three joined on timestamp |

**No CIP→historian mapping.** Tags such as `HMI_PLANT_AUTO` stay independent control features (`writes_*`, `last_value_*`). See `cip_tag_columns.csv` for the tag↔column map.

**Timezone:** PCAP epochs are UTC; merge converts them to `Asia/Singapore` naive wall-clock to match the historian.

## Regenerate

Requires [Wireshark](https://www.wireshark.org/) (`tshark` on PATH), or set `TSHARK_PATH`.

```powershell
cd D:\AI-TDP

# Pilot (2 morning captures) — validate first
python scripts/dataset/extract_swat_cip_writes.py --pilot
python scripts/dataset/extract_swat_network_1s.py --pilot
python scripts/dataset/build_swat_multilayer_dataset.py

# Full corpus (~7.7 GB PCAPs; long-running, hours)
python scripts/dataset/extract_swat_cip_writes.py
python scripts/dataset/extract_swat_network_1s.py
python scripts/dataset/build_swat_multilayer_dataset.py

# Resume interrupted full runs
python scripts/dataset/extract_swat_cip_writes.py --resume
python scripts/dataset/extract_swat_network_1s.py --resume
```

## Notes

- PCAPs: `../SWaT.A12_PCAPs_Mar_26/` (gzip pcapng, ports **44818** / **2222**)
- Summaries: `../../reports/swat/swat_*_summary.json`
