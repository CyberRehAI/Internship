"""Re-inventory IEC-104 balanced CSV feature schemas.

Usage (from AI-TDP root):
  python scripts/dataset/inventory_iec104_features.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = (
    ROOT
    / "data"
    / "iec104"
    / "balanced"
    / "Balanced_IEC104_Train_Test_CSV_Files"
    / "iec104_train_test_csvs"
)
OUT = ROOT / "reports" / "iec104" / "iec104_feature_inventory.json"

FILES = {
    "cic_60_train": BASE / "tests_cic_60" / "train_60_CICIFlow.csv",
    "custom_60_train": BASE / "tests_custom_60" / "train_60_custom_script.csv",
}


def inventory(path: Path) -> dict:
    df = pd.read_csv(path, low_memory=False)
    cols = [c.strip() for c in df.columns]
    label_col = next((c for c in cols if c.lower() == "label"), None)
    entry = {
        "path": str(path.as_posix()),
        "n_rows": int(len(df)),
        "n_cols": int(len(cols)),
        "columns": cols,
    }
    if label_col:
        entry["label_col"] = label_col
        entry["label_counts"] = {
            str(k): int(v) for k, v in df[label_col].value_counts().items()
        }
    return entry


def main() -> None:
    results = {name: inventory(path) for name, path in FILES.items() if path.exists()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for name, entry in results.items():
        print(f"{name}: {entry['n_rows']} rows, {entry['n_cols']} cols")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
