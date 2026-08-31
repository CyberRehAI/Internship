"""Locked feature-group column names for SWaT.A12 multilayer cleaning."""

from __future__ import annotations

from typing import List, Sequence

TIMESTAMP_COL = "t_stamp"

NETWORK_COLS: List[str] = [
    "net_enip_tcp_pkts",
    "net_enip_udp_pkts",
    "net_total_pkts",
    "net_total_bytes",
    "net_unique_src_ips",
    "net_unique_dst_ips",
    "net_packet_rate",
]

DROP_ALARM_COLS: List[str] = [
    "PSH301.Alarm",
    "DPSH301.Alarm",
    "PSH501.Alarm",
    "PSL501.Alarm",
]

# 81 CIP symbolic tags (sorted to match multilayer CSV / cip_tag_columns order variants)
_CIP_TAGS: List[str] = [
    "HMI_1_MV_004",
    "HMI_1_MV_005",
    "HMI_AIT201",
    "HMI_AIT202",
    "HMI_AIT203",
    "HMI_AIT301",
    "HMI_AIT302",
    "HMI_AIT303",
    "HMI_AIT401",
    "HMI_AIT402",
    "HMI_AIT501",
    "HMI_AIT502",
    "HMI_AIT503",
    "HMI_AIT504",
    "HMI_DPIT301",
    "HMI_FIT101",
    "HMI_FIT102",
    "HMI_FIT201",
    "HMI_FIT301",
    "HMI_FIT401",
    "HMI_FIT501",
    "HMI_FIT502",
    "HMI_FIT503",
    "HMI_FIT504",
    "HMI_FIT601",
    "HMI_FIT602",
    "HMI_LIT101",
    "HMI_LIT301",
    "HMI_LIT401",
    "HMI_LIT601",
    "HMI_LIT602",
    "HMI_MV101",
    "HMI_MV201",
    "HMI_MV301",
    "HMI_MV302",
    "HMI_MV303",
    "HMI_MV304",
    "HMI_MV501",
    "HMI_MV502",
    "HMI_MV503",
    "HMI_MV504",
    "HMI_P101",
    "HMI_P102",
    "HMI_P201",
    "HMI_P202",
    "HMI_P203",
    "HMI_P204",
    "HMI_P205",
    "HMI_P206",
    "HMI_P207",
    "HMI_P208",
    "HMI_P2_PERMISSIVE",
    "HMI_P301",
    "HMI_P302",
    "HMI_P3_PERMISSIVE",
    "HMI_P401",
    "HMI_P402",
    "HMI_P403",
    "HMI_P404",
    "HMI_P4_PERMISSIVE",
    "HMI_P501",
    "HMI_P502",
    "HMI_P5_PERMISSIVE",
    "HMI_P5_STATE",
    "HMI_P601",
    "HMI_P602",
    "HMI_P603",
    "HMI_P6_PERMISSIVE",
    "HMI_PIT501",
    "HMI_PIT502",
    "HMI_PIT503",
    "HMI_PLANT",
    "HMI_PLANT_AUTO",
    "HMI_PLANT_RESET",
    "HMI_P_NAOCL_UF_DUTY",
    "HMI_P_RO_FEED_DUTY",
    "HMI_RO_HPP_SD",
    "HMI_SHUTDOWN_FLUSHING",
    "HMI_UV401",
    "P2_P2078_AUTOINP",
    "P6_P602_AUTOINP",
]

WRITE_COLS: List[str] = [f"writes_{t}" for t in _CIP_TAGS]
LAST_VALUE_COLS: List[str] = [f"last_value_{t}" for t in _CIP_TAGS]


def protocol_columns() -> List[str]:
    return WRITE_COLS + LAST_VALUE_COLS


def physical_columns(columns: Sequence[str]) -> List[str]:
    """Physical historian columns: everything except timestamp, net, protocol, dropped alarms."""
    exclude = {
        TIMESTAMP_COL,
        *NETWORK_COLS,
        *WRITE_COLS,
        *LAST_VALUE_COLS,
        *DROP_ALARM_COLS,
    }
    return [c for c in columns if c not in exclude]


def assert_expected_columns(columns: Sequence[str]) -> None:
    """Raise if required network/protocol columns are missing from the header."""
    missing = [c for c in NETWORK_COLS + WRITE_COLS + LAST_VALUE_COLS if c not in columns]
    if missing:
        raise KeyError(f"Missing expected columns ({len(missing)}): {missing[:10]}...")
