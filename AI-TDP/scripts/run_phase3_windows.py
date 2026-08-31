"""Compat shim — prefer scripts/phases/run_phase3_windows.py."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "phases" / "run_phase3_windows.py"
try:
    runpy.run_path(str(_TARGET), run_name="__main__")
except SystemExit as e:
    raise SystemExit(e.code if e.code is not None else 0)
