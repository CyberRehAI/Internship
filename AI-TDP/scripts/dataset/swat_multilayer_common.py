"""Shared helpers for SWaT.A12 multi-layer dataset scripts."""
from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
PCAP_DIR = ROOT / "data" / "swat" / "SWaT.A12_PCAPs_Mar_26"
HISTORIAN_CSV = ROOT / "data" / "swat" / "11-Mar-2026_0900_1700.csv"
OUT_DIR = ROOT / "data" / "swat" / "multilayer"
REPORTS_DIR = ROOT / "reports" / "swat"

CIP_WRITES_CSV = OUT_DIR / "cip_writes.csv"
NETWORK_1S_CSV = OUT_DIR / "network_1s.csv"
MULTILAYER_CSV = OUT_DIR / "swat_multilayer_1s.csv"
TAG_COLUMNS_CSV = OUT_DIR / "cip_tag_columns.csv"
CIP_WRITES_SUMMARY = REPORTS_DIR / "swat_cip_writes_summary.json"
NETWORK_SUMMARY = REPORTS_DIR / "swat_network_1s_summary.json"
MULTILAYER_SUMMARY = REPORTS_DIR / "swat_multilayer_summary.json"

ENIP_TCP_PORT = 44818
ENIP_UDP_PORT = 2222

# Common CIP elementary type codes (Logix Write Tag payload)
_CIP_TYPES = {
    0xC1: ("BOOL", 1),
    0xC2: ("SINT", 1),
    0xC3: ("INT", 2),
    0xC4: ("DINT", 4),
    0xC5: ("LINT", 8),
    0xC6: ("USINT", 1),
    0xC7: ("UINT", 2),
    0xC8: ("UDINT", 4),
    0xCA: ("REAL", 4),
    0xCB: ("LREAL", 8),
}


def find_tshark() -> Path:
    """Locate tshark.exe; raise with install hint if missing."""
    env = os.environ.get("TSHARK_PATH")
    candidates: List[Path] = []
    if env:
        candidates.append(Path(env))
    which = shutil.which("tshark")
    if which:
        candidates.append(Path(which))
    candidates.extend(
        [
            Path(r"C:\Program Files\Wireshark\tshark.exe"),
            Path(r"C:\Program Files (x86)\Wireshark\tshark.exe"),
        ]
    )
    for path in candidates:
        if path and path.is_file():
            return path
    raise FileNotFoundError(
        "tshark not found. Install Wireshark and ensure tshark is on PATH, "
        "or set TSHARK_PATH to tshark.exe. "
        "https://www.wireshark.org/download.html"
    )


def list_pcap_files(pcap_dir: Path = PCAP_DIR) -> List[Path]:
    """Return sorted capture paths (.gz and bare pcapng/pcap)."""
    if not pcap_dir.is_dir():
        raise FileNotFoundError(f"PCAP directory not found: {pcap_dir}")
    files: List[Path] = []
    for p in sorted(pcap_dir.iterdir()):
        if not p.is_file():
            continue
        name = p.name.lower()
        if name.endswith((".gz", ".pcap", ".pcapng")) or name.startswith("ensignpreuat_"):
            files.append(p)
    # Prefer unique stems: if both .gz and unpacked exist, keep both only if distinct names
    return files


def pilot_pcap_files(pcap_dir: Path = PCAP_DIR, n: int = 2) -> List[Path]:
    """Captures near historian start (09:00 on 11-Mar-2026)."""
    all_files = list_pcap_files(pcap_dir)
    # Filenames embed local start time: EnsignPreUAT_NNNNN_YYYYMMDDHHMMSS
    preferred = [
        p
        for p in all_files
        if "2026031109" in p.name or "2026031110" in p.name
    ]
    if preferred:
        return preferred[:n]
    return all_files[:n]


def ensure_out_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_tag_column(tag: str) -> str:
    """Safe column suffix from CIP symbolic tag."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", tag.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "UNKNOWN"
    if s[0].isdigit():
        s = f"T_{s}"
    return s


def parse_cip_data_int(data_hex: str) -> Optional[int]:
    """
    Best-effort integer from CIP write payload hex.

    Handles standard Write Tag layouts (type + pad + count + data) and the
    observed Ensign pattern where a DINT/BOOL value sits at byte offset 4.
    """
    if not data_hex:
        return None
    hex_str = re.sub(r"[^0-9A-Fa-f]", "", data_hex)
    if len(hex_str) % 2:
        hex_str = hex_str[:-1]
    if not hex_str:
        return None
    raw = bytes.fromhex(hex_str)

    if raw and raw[0] in _CIP_TYPES:
        _name, size = _CIP_TYPES[raw[0]]
        # type(1) + reserved(1) + elements(2) + data
        offset = 4
        if len(raw) >= offset + size:
            chunk = raw[offset : offset + size]
            if size == 1:
                return int(chunk[0])
            if size == 2:
                return int(struct.unpack("<H", chunk)[0])
            if size == 4:
                if _name == "REAL":
                    return int(struct.unpack("<f", chunk)[0])
                return int(struct.unpack("<i", chunk)[0])
            if size == 8:
                return int(struct.unpack("<q", chunk)[0])

    # Observed: a0 02 .. .. 01 00 00 00 00 00  → value at offset 4
    if len(raw) >= 8:
        return int(struct.unpack("<i", raw[4:8])[0])
    if len(raw) >= 4:
        return int(struct.unpack("<i", raw[-4:])[0])
    if len(raw) == 1:
        return int(raw[0])
    return None


def run_tshark(args: List[str], tshark: Optional[Path] = None) -> subprocess.CompletedProcess:
    exe = tshark or find_tshark()
    return subprocess.run(
        [str(exe), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def iter_tshark_lines(args: List[str], tshark: Optional[Path] = None) -> Iterable[str]:
    """Stream stdout lines from tshark (for large captures)."""
    exe = tshark or find_tshark()
    proc = subprocess.Popen(
        [str(exe), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.wait()
        # Non-zero is common for truncated/gzip edge cases; caller checks emptiness
