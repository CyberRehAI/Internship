"""
Build per-second EtherNet/IP network summaries from SWaT.A12 PCAPs.

Columns: timestamp, enip_tcp_pkts, enip_udp_pkts, total_pkts, total_bytes,
         unique_src_ips, unique_dst_ips, packet_rate

Usage:
  python scripts/dataset/extract_swat_network_1s.py --pilot
  python scripts/dataset/extract_swat_network_1s.py
  python scripts/dataset/extract_swat_network_1s.py --resume
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swat_multilayer_common import (
    ENIP_TCP_PORT,
    ENIP_UDP_PORT,
    NETWORK_1S_CSV,
    NETWORK_SUMMARY,
    OUT_DIR,
    ensure_out_dirs,
    find_tshark,
    iter_tshark_lines,
    list_pcap_files,
    pilot_pcap_files,
)

FIELDNAMES = [
    "timestamp",
    "enip_tcp_pkts",
    "enip_udp_pkts",
    "total_pkts",
    "total_bytes",
    "unique_src_ips",
    "unique_dst_ips",
    "packet_rate",
]

PROGRESS_JSON = OUT_DIR / "network_1s_progress.json"
DISPLAY_FILTER = f"tcp.port == {ENIP_TCP_PORT} || udp.port == {ENIP_UDP_PORT}"


def _load_done() -> Set[str]:
    if not PROGRESS_JSON.is_file():
        return set()
    try:
        return set(json.loads(PROGRESS_JSON.read_text(encoding="utf-8")).get("done_files", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_done(done: Set[str]) -> None:
    PROGRESS_JSON.write_text(
        json.dumps({"done_files": sorted(done)}, indent=2),
        encoding="utf-8",
    )


# second -> aggregates
Agg = Dict[str, object]


def _new_agg() -> Agg:
    return {
        "enip_tcp_pkts": 0,
        "enip_udp_pkts": 0,
        "total_pkts": 0,
        "total_bytes": 0,
        "srcs": set(),
        "dsts": set(),
    }


def accumulate_pcap(pcap: Path, tshark: Path, bins: DefaultDict[int, Agg]) -> int:
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
        "frame.len",
        "-e",
        "ip.src",
        "-e",
        "ip.dst",
        "-e",
        "tcp.dstport",
        "-e",
        "tcp.srcport",
        "-e",
        "udp.dstport",
        "-e",
        "udp.srcport",
    ]
    n = 0
    for line in iter_tshark_lines(args, tshark=tshark):
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 8:
            parts.append("")
        ts_s, flen, src, dst, td, tsport, ud, usport = parts[:8]
        try:
            sec = int(float(ts_s))
        except ValueError:
            continue
        try:
            length = int(flen) if flen else 0
        except ValueError:
            length = 0

        ports = {td, tsport, ud, usport}
        is_tcp = str(ENIP_TCP_PORT) in ports
        is_udp = str(ENIP_UDP_PORT) in ports
        if not (is_tcp or is_udp):
            continue

        a = bins[sec]
        a["total_pkts"] = int(a["total_pkts"]) + 1
        a["total_bytes"] = int(a["total_bytes"]) + length
        if is_tcp:
            a["enip_tcp_pkts"] = int(a["enip_tcp_pkts"]) + 1
        if is_udp:
            a["enip_udp_pkts"] = int(a["enip_udp_pkts"]) + 1
        if src:
            a["srcs"].add(src)  # type: ignore[union-attr]
        if dst:
            a["dsts"].add(dst)  # type: ignore[union-attr]
        n += 1
    return n


def bins_to_rows(bins: DefaultDict[int, Agg]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for sec in sorted(bins):
        a = bins[sec]
        rows.append(
            {
                "timestamp": sec,
                "enip_tcp_pkts": a["enip_tcp_pkts"],
                "enip_udp_pkts": a["enip_udp_pkts"],
                "total_pkts": a["total_pkts"],
                "total_bytes": a["total_bytes"],
                "unique_src_ips": len(a["srcs"]),  # type: ignore[arg-type]
                "unique_dst_ips": len(a["dsts"]),  # type: ignore[arg-type]
                "packet_rate": a["total_pkts"],  # pkts in 1s bin
            }
        )
    return rows


def merge_existing_csv(path: Path, bins: DefaultDict[int, Agg]) -> None:
    """Re-load prior per-second rows into bins (unique IP counts not recoverable exactly)."""
    if not path.is_file():
        return
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sec = int(float(row["timestamp"]))
            a = bins[sec]
            a["enip_tcp_pkts"] = int(a["enip_tcp_pkts"]) + int(row["enip_tcp_pkts"])
            a["enip_udp_pkts"] = int(a["enip_udp_pkts"]) + int(row["enip_udp_pkts"])
            a["total_pkts"] = int(a["total_pkts"]) + int(row["total_pkts"])
            a["total_bytes"] = int(a["total_bytes"]) + int(row["total_bytes"])
            # Approximate unique IPs as max seen (cannot union across files from CSV alone)
            a["_max_src"] = max(int(a.get("_max_src", 0)), int(row["unique_src_ips"]))  # type: ignore[arg-type]
            a["_max_dst"] = max(int(a.get("_max_dst", 0)), int(row["unique_dst_ips"]))  # type: ignore[arg-type]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract SWaT ENIP 1s network summaries")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit-files", type=int, default=None)
    args = parser.parse_args()

    ensure_out_dirs()
    tshark = find_tshark()
    print(f"Using tshark: {tshark}")

    files = pilot_pcap_files() if args.pilot else list_pcap_files()
    if args.limit_files is not None:
        files = files[: args.limit_files]

    done = _load_done() if args.resume else set()
    bins: DefaultDict[int, Agg] = defaultdict(_new_agg)

    # Full recompute in memory across selected files (unique IPs accurate within run)
    if args.resume and NETWORK_1S_CSV.is_file() and done:
        print("Resume: recomputing from remaining files and rewriting merged CSV")
        # Keep already-done files by re-processing is expensive; instead re-scan only pending
        # and merge packet counts from existing CSV (unique IPs use max approximation for old bins)
        merge_existing_csv(NETWORK_1S_CSV, bins)

    if not args.resume and NETWORK_1S_CSV.is_file():
        NETWORK_1S_CSV.unlink()
        done = set()

    total_pkts = 0
    for i, pcap in enumerate(files, 1):
        if pcap.name in done:
            print(f"[{i}/{len(files)}] skip {pcap.name}")
            continue
        print(f"[{i}/{len(files)}] {pcap.name} …", flush=True)
        n = accumulate_pcap(pcap, tshark, bins)
        total_pkts += n
        done.add(pcap.name)
        _save_done(done)
        print(f"  -> {n} ENIP packets (session pkts {total_pkts})", flush=True)

        # Periodic flush so crash does not lose all progress
        rows = bins_to_rows(bins)
        # Fix unique IP approx for merged-from-csv bins
        for row in rows:
            sec = int(row["timestamp"])
            a = bins[sec]
            if not a["srcs"] and "_max_src" in a:  # type: ignore[operator]
                row["unique_src_ips"] = a["_max_src"]
                row["unique_dst_ips"] = a["_max_dst"]
        with NETWORK_1S_CSV.open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    rows = bins_to_rows(bins)
    for row in rows:
        sec = int(row["timestamp"])
        a = bins[sec]
        if not a["srcs"] and "_max_src" in a:  # type: ignore[operator]
            row["unique_src_ips"] = a["_max_src"]
            row["unique_dst_ips"] = a["_max_dst"]

    with NETWORK_1S_CSV.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "n_seconds": len(rows),
        "n_files_done": len(done),
        "total_pkts_this_run": total_pkts,
        "time_start": rows[0]["timestamp"] if rows else None,
        "time_end": rows[-1]["timestamp"] if rows else None,
        "output": str(NETWORK_1S_CSV.as_posix()),
    }
    NETWORK_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {NETWORK_1S_CSV} ({len(rows)} seconds)")
    print(f"Summary: {NETWORK_SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
