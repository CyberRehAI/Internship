"""
Extract CIP Write Tag requests from SWaT.A12 PCAP/PCAPNG captures.

Writes independent control-command rows (symbolic CIP tags as-is).

Usage (from AI-TDP root):
  python scripts/dataset/extract_swat_cip_writes.py --pilot
  python scripts/dataset/extract_swat_cip_writes.py
  python scripts/dataset/extract_swat_cip_writes.py --resume
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

# Allow running as script from repo root or scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_multilayer_common import (
    CIP_WRITES_CSV,
    CIP_WRITES_SUMMARY,
    OUT_DIR,
    ensure_out_dirs,
    find_tshark,
    iter_tshark_lines,
    list_pcap_files,
    parse_cip_data_int,
    pilot_pcap_files,
)

FIELDNAMES = [
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "cip.service",
    "tag_name",
    "data",
    "data_int",
    "source_file",
]

DISPLAY_FILTER = (
    "(cip.service == 0x4d || cip.service == 0x53 || cip.service == 0x10) "
    "&& cip.rr == 0"
)

PROGRESS_JSON = OUT_DIR / "cip_writes_progress.json"


def _load_done() -> Set[str]:
    if not PROGRESS_JSON.is_file():
        return set()
    try:
        data = json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
        return set(data.get("done_files", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_done(done: Set[str]) -> None:
    PROGRESS_JSON.write_text(
        json.dumps({"done_files": sorted(done)}, indent=2),
        encoding="utf-8",
    )


def extract_from_pcap(pcap: Path, tshark: Path) -> Iterable[Dict[str, str]]:
    args = [
        "-r",
        str(pcap),
        "-Y",
        DISPLAY_FILTER,
        "-T",
        "fields",
        "-E",
        "separator=\t",
        "-E",
        "occurrence=f",
        "-e",
        "frame.time_epoch",
        "-e",
        "ip.src",
        "-e",
        "ip.dst",
        "-e",
        "cip.service",
        "-e",
        "cip.symbol",
        "-e",
        "cip.data",
    ]
    for line in iter_tshark_lines(args, tshark=tshark):
        if not line.strip():
            continue
        parts = line.split("\t")
        # Pad missing fields
        while len(parts) < 6:
            parts.append("")
        ts, src, dst, service, symbol, data = parts[:6]
        # Multiple Service Packet may emit comma-separated services/symbols
        services = [s.strip() for s in service.split(",") if s.strip()]
        symbols = [s.strip() for s in symbol.split(",") if s.strip()]
        datas = [d.strip() for d in data.split(",") if d.strip()] if data else [""]

        # Prefer Write Tag service token if present in multi-service frames
        svc = "0x4d" if any(s.lower() == "0x4d" for s in services) else (services[0] if services else service)

        if not symbols:
            # Still emit with empty tag if service matched (rare)
            symbols = [""]

        # Pair symbols with data segments when lengths match; else reuse last data
        for i, tag in enumerate(symbols):
            dhex = datas[i] if i < len(datas) else (datas[-1] if datas else "")
            dhex = dhex.replace(":", "")
            parsed = parse_cip_data_int(dhex)
            yield {
                "frame.time_epoch": ts,
                "ip.src": src,
                "ip.dst": dst,
                "cip.service": svc,
                "tag_name": tag,
                "data": dhex,
                "data_int": "" if parsed is None else str(parsed),
                "source_file": pcap.name,
            }


def write_summary(rows_seen: int, tag_counts: Counter, files: List[str]) -> None:
    summary = {
        "n_rows": rows_seen,
        "n_files": len(files),
        "files": files,
        "unique_tags": len(tag_counts),
        "tag_counts": dict(tag_counts.most_common()),
        "output": str(CIP_WRITES_CSV.as_posix()),
    }
    CIP_WRITES_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract SWaT CIP write requests")
    parser.add_argument("--pilot", action="store_true", help="Process 2 morning captures only")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed files")
    parser.add_argument("--limit-files", type=int, default=None, help="Max files to process")
    args = parser.parse_args()

    ensure_out_dirs()
    tshark = find_tshark()
    print(f"Using tshark: {tshark}")

    files = pilot_pcap_files() if args.pilot else list_pcap_files()
    if args.limit_files is not None:
        files = files[: args.limit_files]

    done = _load_done() if args.resume else set()
    write_header = not CIP_WRITES_CSV.is_file() or not args.resume or CIP_WRITES_CSV.stat().st_size == 0
    if not args.resume and CIP_WRITES_CSV.is_file():
        CIP_WRITES_CSV.unlink()
        write_header = True
        done = set()

    tag_counts: Counter = Counter()
    rows_seen = 0
    processed_files: List[str] = []

    # If resuming, seed tag counts from existing CSV lightly (optional skip for speed)
    if args.resume and CIP_WRITES_CSV.is_file():
        with CIP_WRITES_CSV.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows_seen += 1
                if row.get("tag_name"):
                    tag_counts[row["tag_name"]] += 1

    mode = "a" if args.resume and CIP_WRITES_CSV.is_file() else "w"
    with CIP_WRITES_CSV.open(mode, newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        if write_header or mode == "w":
            writer.writeheader()

        for i, pcap in enumerate(files, 1):
            if pcap.name in done:
                print(f"[{i}/{len(files)}] skip {pcap.name}")
                continue
            print(f"[{i}/{len(files)}] {pcap.name} …", flush=True)
            n_file = 0
            try:
                for row in extract_from_pcap(pcap, tshark):
                    writer.writerow(row)
                    n_file += 1
                    rows_seen += 1
                    if row["tag_name"]:
                        tag_counts[row["tag_name"]] += 1
            except Exception as exc:  # noqa: BLE001 — continue other files
                print(f"  ERROR: {exc}", flush=True)
            out.flush()
            done.add(pcap.name)
            processed_files.append(pcap.name)
            _save_done(done)
            print(f"  -> {n_file} writes (total {rows_seen})", flush=True)

    write_summary(rows_seen, tag_counts, sorted(done) if done else processed_files)
    print(f"Wrote {CIP_WRITES_CSV} ({rows_seen} rows, {len(tag_counts)} tags)")
    print(f"Summary: {CIP_WRITES_SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
