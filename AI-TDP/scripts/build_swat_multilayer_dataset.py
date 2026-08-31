"""Compat shim — prefer scripts/dataset/build_swat_multilayer_dataset.py."""
from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "dataset" / "build_swat_multilayer_dataset.py"
try:
    runpy.run_path(str(_TARGET), run_name="__main__")
except SystemExit as e:
    raise SystemExit(e.code if e.code is not None else 0)
