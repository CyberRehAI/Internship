"""
Extract CICFlowMeter-style flow features from ELEGANT PCAP/PCAPNG captures.

- Reads pcapng via dpkt
- Builds bidirectional IPv4 TCP/UDP flows
- Adds Modbus/TCP (port 502) function-code stats
- Labels from scenario folder + UDP attack-marker time windows
- Writes per-capture CSVs and a combined train-ready CSV

Usage (from AI-TDP root):
  python scripts/dataset/extract_elegant_flows.py
  python scripts/dataset/extract_elegant_flows.py --max-caps-per-archive 3
"""
from __future__ import annotations

import argparse
import csv
import math
import shutil
import tarfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import dpkt

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ROOT = ROOT / "data" / "elegant" / "IEEE_DataPort"
WORK_ROOT = ROOT / "data" / "elegant" / "work_pcaps"
OUT_ROOT = ROOT / "data" / "elegant" / "flows"
REPORT_JSON = ROOT / "reports" / "elegant" / "elegant_flows_summary.json"

FLOW_IDLE_TIMEOUT = 120.0  # seconds — emit if no packets
FLOW_SLICE = 30.0  # seconds — tumble long-lived Modbus sessions into samples
ACTIVE_IDLE_GAP = 1.0

# Scenario plans: (archive_path, scenario_label, max_caps or None=all)
DEFAULT_JOBS = [
    ("MiTM/normal_PLC_traffic.tar.gz", "normal", None),
    ("MiTM/MiTM_ARP_Poisoning.tar.gz", "mitm_arp", None),
    ("MiTM/MiTM_Full_Chain.tar.gz", "mitm_full_chain", None),
    ("DoS/single_flood_rate_1_t1.zip", "dos_flood", None),
    ("DoS/single_flood_rate_1_t2.zip", "dos_flood", None),
    ("DoS/single_flood_rate_2_t1.zip", "dos_flood", 5),
    ("DoS/single_flood_rate_2_t2.zip", "dos_flood", 5),
    ("DoS/single_amp_t1.zip", "dos_amp", 5),
    ("DoS/single_amp_t2.zip", "dos_amp", 5),
    ("DoS/multiple_flood_0100_0125.tar.gz", "dos_flood", 3),
    ("DoS/multiple_amp_0130_0200.tar.gz", "dos_amp", 3),
]


def _stats(values: List[float]) -> Tuple[float, float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    mn = min(values)
    mx = max(values)
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mn, mx, mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mn, mx, mean, math.sqrt(var)


def _active_idle(times: List[float], gap: float = ACTIVE_IDLE_GAP) -> Tuple[List[float], List[float]]:
    if len(times) < 2:
        return [], []
    active, idle = [], []
    start = times[0]
    prev = times[0]
    for t in times[1:]:
        dt = t - prev
        if dt > gap:
            active.append(prev - start)
            idle.append(dt)
            start = t
        prev = t
    active.append(prev - start)
    return active, idle


@dataclass
class Flow:
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    proto: int
    start: float
    end: float
    fwd_lens: List[int] = field(default_factory=list)
    bwd_lens: List[int] = field(default_factory=list)
    times: List[float] = field(default_factory=list)
    fwd_times: List[float] = field(default_factory=list)
    bwd_times: List[float] = field(default_factory=list)
    fin: int = 0
    syn: int = 0
    rst: int = 0
    psh: int = 0
    ack: int = 0
    urg: int = 0
    ece: int = 0
    cwe: int = 0
    fwd_psh: int = 0
    bwd_psh: int = 0
    fwd_urg: int = 0
    bwd_urg: int = 0
    fwd_header: int = 0
    bwd_header: int = 0
    init_fwd_win: int = -1
    init_bwd_win: int = -1
    modbus_fn: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    modbus_pkts: int = 0

    def key(self) -> Tuple:
        return (self.src_ip, self.src_port, self.dst_ip, self.dst_port, self.proto)


def _bidir_key(sip: str, sport: int, dip: str, dport: int, proto: int) -> Tuple:
    a = (sip, sport)
    b = (dip, dport)
    if a <= b:
        return (sip, sport, dip, dport, proto, True)
    return (dip, dport, sip, sport, proto, False)


def _inet_to_str(addr: bytes) -> str:
    return ".".join(str(b) for b in addr)


def _parse_modbus_fn(payload: bytes) -> Optional[int]:
    # MBAP: tx(2) proto(2)=0 len(2) unit(1) fn(1)
    if len(payload) < 8:
        return None
    proto_id = int.from_bytes(payload[2:4], "big")
    if proto_id != 0:
        return None
    return payload[7]


def iter_packets(path: Path) -> Iterator[Tuple[float, bytes]]:
    with open(path, "rb") as f:
        magic = f.read(4)
        f.seek(0)
        if magic == b"\n\r\r\n":
            reader = dpkt.pcapng.Reader(f)
        elif magic in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
            reader = dpkt.pcap.Reader(f)
        else:
            # fallback try pcapng then pcap
            try:
                reader = dpkt.pcapng.Reader(f)
            except Exception:
                f.seek(0)
                reader = dpkt.pcap.Reader(f)
        for ts, buf in reader:
            yield float(ts), buf


def find_attack_windows(path: Path) -> List[Tuple[float, float, str]]:
    """Return list of (start_ts, end_ts, kind) from UDP marker payloads."""
    starts: List[Tuple[float, str]] = []
    ends: List[Tuple[float, str]] = []
    for ts, buf in iter_packets(path):
        try:
            eth = dpkt.ethernet.Ethernet(buf)
        except Exception:
            continue
        if not isinstance(eth.data, dpkt.ip.IP):
            continue
        ip = eth.data
        if not isinstance(ip.data, dpkt.udp.UDP):
            continue
        udp = ip.data
        payload = bytes(udp.data or b"")
        if not payload:
            continue
        text = payload.decode("utf-8", errors="ignore")
        upper = text.upper()
        if "ATTACK_START" in upper or "MITM_ATTACK_START" in upper:
            kind = "mitm" if "MITM" in upper else "dos"
            starts.append((ts, kind))
        elif "ATTACK_END" in upper or "MITM_ATTACK_END" in upper:
            kind = "mitm" if "MITM" in upper else "dos"
            ends.append((ts, kind))

    windows: List[Tuple[float, float, str]] = []
    # pair starts with next end of same kind
    end_idx = 0
    for st, kind in starts:
        match_end = None
        for j in range(end_idx, len(ends)):
            et, ek = ends[j]
            if ek == kind and et >= st:
                match_end = et
                end_idx = j + 1
                break
        if match_end is None:
            # open-ended: until +3600s or file end later
            match_end = st + 3600.0
        windows.append((st, match_end, kind))
    return windows


def update_flow(flow: Flow, ts: float, length: int, forward: bool, tcp: Optional[dpkt.tcp.TCP], payload: bytes) -> None:
    flow.end = ts
    flow.times.append(ts)
    if forward:
        flow.fwd_lens.append(length)
        flow.fwd_times.append(ts)
        if tcp is not None:
            flow.fwd_header += (tcp.off * 4) if hasattr(tcp, "off") else 20
            if flow.init_fwd_win < 0:
                flow.init_fwd_win = int(tcp.win)
            if tcp.flags & dpkt.tcp.TH_PUSH:
                flow.fwd_psh += 1
            if tcp.flags & dpkt.tcp.TH_URG:
                flow.fwd_urg += 1
    else:
        flow.bwd_lens.append(length)
        flow.bwd_times.append(ts)
        if tcp is not None:
            flow.bwd_header += (tcp.off * 4) if hasattr(tcp, "off") else 20
            if flow.init_bwd_win < 0:
                flow.init_bwd_win = int(tcp.win)
            if tcp.flags & dpkt.tcp.TH_PUSH:
                flow.bwd_psh += 1
            if tcp.flags & dpkt.tcp.TH_URG:
                flow.bwd_urg += 1

    if tcp is not None:
        fl = tcp.flags
        if fl & dpkt.tcp.TH_FIN:
            flow.fin += 1
        if fl & dpkt.tcp.TH_SYN:
            flow.syn += 1
        if fl & dpkt.tcp.TH_RST:
            flow.rst += 1
        if fl & dpkt.tcp.TH_PUSH:
            flow.psh += 1
        if fl & dpkt.tcp.TH_ACK:
            flow.ack += 1
        if fl & dpkt.tcp.TH_URG:
            flow.urg += 1
        if fl & 0x40:  # ECE
            flow.ece += 1
        if fl & 0x80:  # CWR
            flow.cwe += 1

    # Modbus on either side of port 502
    if flow.src_port == 502 or flow.dst_port == 502:
        fn = _parse_modbus_fn(payload)
        if fn is not None:
            flow.modbus_pkts += 1
            flow.modbus_fn[fn] += 1


def flow_to_row(
    flow: Flow,
    scenario: str,
    source_file: str,
    windows: List[Tuple[float, float, str]],
) -> Dict[str, Any]:
    duration = max(flow.end - flow.start, 1e-6)
    fwd_pkts = len(flow.fwd_lens)
    bwd_pkts = len(flow.bwd_lens)
    tot_fwd = sum(flow.fwd_lens)
    tot_bwd = sum(flow.bwd_lens)
    tot_pkts = fwd_pkts + bwd_pkts
    tot_bytes = tot_fwd + tot_bwd

    fmin, fmax, fmean, fstd = _stats([float(x) for x in flow.fwd_lens])
    bmin, bmax, bmean, bstd = _stats([float(x) for x in flow.bwd_lens])
    all_lens = [float(x) for x in flow.fwd_lens + flow.bwd_lens]
    pmin, pmax, pmean, pstd = _stats(all_lens)
    pvar = pstd**2

    def iats(times: List[float]) -> List[float]:
        return [times[i] - times[i - 1] for i in range(1, len(times))]

    fi_min, fi_max, fi_mean, fi_std = _stats(iats(flow.times))
    fwd_i = iats(flow.fwd_times)
    bwd_i = iats(flow.bwd_times)
    fwi_min, fwi_max, fwi_mean, fwi_std = _stats(fwd_i)
    bwi_min, bwi_max, bwi_mean, bwi_std = _stats(bwd_i)

    active, idle = _active_idle(flow.times)
    a_min, a_max, a_mean, a_std = _stats(active)
    i_min, i_max, i_mean, i_std = _stats(idle)

    # Label: if overlapping an attack window, use scenario; if scenario is normal, always normal;
    # if no windows found in an attack capture, default to scenario for all flows.
    mid = (flow.start + flow.end) / 2.0
    in_window = any(st <= mid <= et for st, et, _ in windows)
    if scenario == "normal":
        label = "normal"
    elif windows:
        label = scenario if in_window else "normal"
    else:
        label = scenario

    modbus_fn3 = int(flow.modbus_fn.get(3, 0))
    modbus_other = int(sum(v for k, v in flow.modbus_fn.items() if k != 3))

    return {
        "Flow ID": f"{flow.src_ip}-{flow.src_port}-{flow.dst_ip}-{flow.dst_port}-{flow.proto}",
        "Src IP": flow.src_ip,
        "Src Port": flow.src_port,
        "Dst IP": flow.dst_ip,
        "Dst Port": flow.dst_port,
        "Protocol": flow.proto,
        "Timestamp": flow.start,
        "Flow Duration": duration,
        "Tot Fwd Pkts": fwd_pkts,
        "Tot Bwd Pkts": bwd_pkts,
        "TotLen Fwd Pkts": tot_fwd,
        "TotLen Bwd Pkts": tot_bwd,
        "Fwd Pkt Len Max": fmax,
        "Fwd Pkt Len Min": fmin,
        "Fwd Pkt Len Mean": fmean,
        "Fwd Pkt Len Std": fstd,
        "Bwd Pkt Len Max": bmax,
        "Bwd Pkt Len Min": bmin,
        "Bwd Pkt Len Mean": bmean,
        "Bwd Pkt Len Std": bstd,
        "Flow Byts/s": tot_bytes / duration,
        "Flow Pkts/s": tot_pkts / duration,
        "Flow IAT Mean": fi_mean,
        "Flow IAT Std": fi_std,
        "Flow IAT Max": fi_max,
        "Flow IAT Min": fi_min,
        "Fwd IAT Tot": sum(fwd_i) if fwd_i else 0.0,
        "Fwd IAT Mean": fwi_mean,
        "Fwd IAT Std": fwi_std,
        "Fwd IAT Max": fwi_max,
        "Fwd IAT Min": fwi_min,
        "Bwd IAT Tot": sum(bwd_i) if bwd_i else 0.0,
        "Bwd IAT Mean": bwi_mean,
        "Bwd IAT Std": bwi_std,
        "Bwd IAT Max": bwi_max,
        "Bwd IAT Min": bwi_min,
        "Fwd PSH Flags": flow.fwd_psh,
        "Bwd PSH Flags": flow.bwd_psh,
        "Fwd URG Flags": flow.fwd_urg,
        "Bwd URG Flags": flow.bwd_urg,
        "Fwd Header Len": flow.fwd_header,
        "Bwd Header Len": flow.bwd_header,
        "Fwd Pkts/s": fwd_pkts / duration,
        "Bwd Pkts/s": bwd_pkts / duration,
        "Pkt Len Min": pmin,
        "Pkt Len Max": pmax,
        "Pkt Len Mean": pmean,
        "Pkt Len Std": pstd,
        "Pkt Len Var": pvar,
        "FIN Flag Cnt": flow.fin,
        "SYN Flag Cnt": flow.syn,
        "RST Flag Cnt": flow.rst,
        "PSH Flag Cnt": flow.psh,
        "ACK Flag Cnt": flow.ack,
        "URG Flag Cnt": flow.urg,
        "CWE Flag Count": flow.cwe,
        "ECE Flag Cnt": flow.ece,
        "Down/Up Ratio": (bwd_pkts / fwd_pkts) if fwd_pkts else 0.0,
        "Pkt Size Avg": pmean,
        "Fwd Seg Size Avg": fmean,
        "Bwd Seg Size Avg": bmean,
        "Init Fwd Win Byts": max(flow.init_fwd_win, 0),
        "Init Bwd Win Byts": max(flow.init_bwd_win, 0),
        "Active Mean": a_mean,
        "Active Std": a_std,
        "Active Max": a_max,
        "Active Min": a_min,
        "Idle Mean": i_mean,
        "Idle Std": i_std,
        "Idle Max": i_max,
        "Idle Min": i_min,
        "Modbus Pkts": flow.modbus_pkts,
        "Modbus Fn3 Count": modbus_fn3,
        "Modbus Fn Other Count": modbus_other,
        "Scenario": scenario,
        "SourceFile": source_file,
        "InAttackWindow": int(in_window) if windows else int(scenario != "normal"),
        "Label": label,
    }


def extract_flows_from_pcap(path: Path, scenario: str) -> List[Dict[str, Any]]:
    windows = find_attack_windows(path)
    open_flows: Dict[Tuple, Flow] = {}
    closed: List[Flow] = []

    def close_flow(key: Tuple) -> None:
        fl = open_flows.pop(key, None)
        if fl is not None:
            closed.append(fl)

    def close_idle_and_slices(now: float) -> None:
        doomed = []
        for k, fl in open_flows.items():
            if now - fl.end > FLOW_IDLE_TIMEOUT:
                doomed.append(k)
            elif now - fl.start >= FLOW_SLICE:
                doomed.append(k)
        for k in doomed:
            close_flow(k)

    pkt_n = 0
    for ts, buf in iter_packets(path):
        pkt_n += 1
        if pkt_n % 20000 == 0:
            close_idle_and_slices(ts)
        try:
            eth = dpkt.ethernet.Ethernet(buf)
        except Exception:
            continue
        if not isinstance(eth.data, dpkt.ip.IP):
            continue
        ip = eth.data
        sip = _inet_to_str(ip.src)
        dip = _inet_to_str(ip.dst)
        tcp = None
        sport = dport = 0
        payload = b""
        if isinstance(ip.data, dpkt.tcp.TCP):
            tcp = ip.data
            proto = 6
            sport = int(tcp.sport)
            dport = int(tcp.dport)
            payload = bytes(tcp.data or b"")
        elif isinstance(ip.data, dpkt.udp.UDP):
            udp = ip.data
            proto = 17
            sport = int(udp.sport)
            dport = int(udp.dport)
            payload = bytes(udp.data or b"")
        else:
            continue

        csip, csport, cdip, cdport, cproto, _ = _bidir_key(sip, sport, dip, dport, proto)
        key5 = (csip, csport, cdip, cdport, cproto)

        fl = open_flows.get(key5)
        if fl is not None and (ts - fl.start) >= FLOW_SLICE:
            close_flow(key5)
            fl = None
        if fl is None:
            fl = Flow(
                src_ip=csip,
                src_port=csport,
                dst_ip=cdip,
                dst_port=cdport,
                proto=cproto,
                start=ts,
                end=ts,
            )
            open_flows[key5] = fl
        length = int(ip.len) if hasattr(ip, "len") else len(buf)
        is_fwd = sip == csip and sport == csport
        update_flow(fl, ts, length, is_fwd, tcp, payload)

        if tcp is not None and (tcp.flags & dpkt.tcp.TH_RST):
            close_flow(key5)

    closed.extend(open_flows.values())
    rows = [
        flow_to_row(fl, scenario, path.name, windows)
        for fl in closed
        if (len(fl.fwd_lens) + len(fl.bwd_lens)) >= 1
    ]

    # DoS floods create huge numbers of 1-packet random-source flows.
    # Keep all multi-packet flows; reservoir-sample short floods.
    if scenario.startswith("dos_") and len(rows) > 8000:
        import random

        multi = [r for r in rows if (r["Tot Fwd Pkts"] + r["Tot Bwd Pkts"]) >= 2]
        single = [r for r in rows if (r["Tot Fwd Pkts"] + r["Tot Bwd Pkts"]) < 2]
        keep_single = min(len(single), max(2000, 8000 - len(multi)))
        if len(single) > keep_single:
            single = random.sample(single, keep_single)
        rows = multi + single
    return rows


FIELDNAMES: Optional[List[str]] = None


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    global FIELDNAMES
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if FIELDNAMES is None:
        FIELDNAMES = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


def list_cap_members(archive: Path) -> List[str]:
    names: List[str] = []
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                base = Path(n).name
                if base.startswith("cap_") and "__MACOSX" not in n and not base.startswith("._"):
                    names.append(n)
    else:
        with tarfile.open(archive, "r:*") as t:
            for m in t.getmembers():
                if not m.isfile():
                    continue
                base = Path(m.name).name
                if base.startswith("cap_") and not base.startswith("._"):
                    names.append(m.name)
    return sorted(names)


def extract_selected(archive: Path, dest: Path, members: List[str]) -> List[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    out_paths: List[Path] = []
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            for n in members:
                target = dest / Path(n).name
                if not target.exists():
                    with z.open(n) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                out_paths.append(target)
    else:
        with tarfile.open(archive, "r:*") as t:
            for n in members:
                target = dest / Path(n).name
                if not target.exists():
                    member = t.getmember(n)
                    f = t.extractfile(member)
                    if f is None:
                        continue
                    with open(target, "wb") as dst:
                        shutil.copyfileobj(f, dst)
                out_paths.append(target)
    return out_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-caps-per-archive", type=int, default=None, help="Override per-job cap limits")
    parser.add_argument("--skip-large", action="store_true", help="Only process MiTM/normal/flood_rate1")
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    jobs = DEFAULT_JOBS
    if args.skip_large:
        jobs = [j for j in jobs if "rate_2" not in j[0] and "amp" not in j[0] and "multiple" not in j[0]]

    summary = {"files": [], "label_counts": defaultdict(int), "total_flows": 0}
    all_rows: List[Dict[str, Any]] = []

    for rel, scenario, default_limit in jobs:
        archive = ARCHIVE_ROOT / rel
        if not archive.exists():
            print(f"[skip missing] {archive}")
            continue
        members = list_cap_members(archive)
        limit = args.max_caps_per_archive if args.max_caps_per_archive is not None else default_limit
        if limit is not None:
            members = members[:limit]
        print(f"\n=== {rel} scenario={scenario} caps={len(members)} ===")
        work_dir = WORK_ROOT / scenario / archive.stem.replace(".tar", "")
        paths = extract_selected(archive, work_dir, members)
        for p in paths:
            print(f"  extracting flows: {p.name} ...", flush=True)
            try:
                rows = extract_flows_from_pcap(p, scenario)
            except Exception as e:
                print(f"  ERROR {p.name}: {e}")
                continue
            out_csv = OUT_ROOT / f"{scenario}__{p.name}.csv"
            write_csv(out_csv, rows)
            all_rows.extend(rows)
            labels = defaultdict(int)
            for r in rows:
                labels[r["Label"]] += 1
                summary["label_counts"][r["Label"]] += 1
            summary["files"].append(
                {
                    "pcap": str(p.as_posix()),
                    "csv": str(out_csv.as_posix()),
                    "scenario": scenario,
                    "n_flows": len(rows),
                    "labels": dict(labels),
                }
            )
            summary["total_flows"] += len(rows)
            print(f"  -> {len(rows)} flows {dict(labels)}")

    combined = OUT_ROOT / "elegant_flows_all.csv"
    write_csv(combined, all_rows)
    summary["combined_csv"] = str(combined.as_posix())
    summary["label_counts"] = dict(summary["label_counts"])

    # simple stratified peek / class balance note
    import json

    REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {combined} ({len(all_rows)} flows)")
    print(f"Label counts: {dict(summary['label_counts'])}")
    print(f"Summary: {REPORT_JSON}")


if __name__ == "__main__":
    main()
