"""Compat shim — prefer scripts/dataset/extract_swat_cip_writes.py."""
from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "dataset" / "extract_swat_cip_writes.py"
try:
    runpy.run_path(str(_TARGET), run_name="__main__")
except SystemExit as e:
    raise SystemExit(e.code if e.code is not None else 0)
