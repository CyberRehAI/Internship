"""
Train Network-domain LSTM-AE baseline (compat wrapper).

Prefer:
  python -m baselines.train.train_lstm_ae --mode net

Usage (from AI-TDP root):
  python scripts/shims/train_network_lstm_ae.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.train.train_lstm_ae import main

if __name__ == "__main__":
    if "--mode" not in sys.argv:
        sys.argv.extend(["--mode", "net"])
    if "--out-dir" not in sys.argv:
        sys.argv.extend(
            ["--out-dir", str(ROOT / "baselines" / "outputs" / "lstm_ae_net")]
        )
    raise SystemExit(main())
