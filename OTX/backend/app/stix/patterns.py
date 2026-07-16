from __future__ import annotations

import re
from dataclasses import dataclass

_YARA_RULE_RE = re.compile(r"\brule\s+\w+", re.IGNORECASE)
_HASH_LENGTHS = {32: "FileHash-MD5", 40: "FileHash-SHA1", 64: "FileHash-SHA256"}


def _escape_stix_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@dataclass
class PatternResult:
    pattern: str
    pattern_type: str = "stix"
    valid: bool = True
    fallback: bool = False
    yara_reclassified: bool = False


def is_yara_rule(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if not _YARA_RULE_RE.search(text):
        return False
    lower = text.lower()
    return "condition:" in lower or "strings:" in lower or "meta:" in lower


def detect_file_hash(value: str) -> str | None:
    text = (value or "").strip()
    if re.fullmatch(r"[a-fA-F0-9]+", text):
        return _HASH_LENGTHS.get(len(text))
    return None


def build_indicator_pattern(ioc_type: str, value: str) -> PatternResult:
    ioc_type = (ioc_type or "").strip()
    value = (value or "").strip()
    if not value:
        return PatternResult(pattern="[x-otx-empty:value = '']", valid=False, fallback=True)

    escaped = _escape_stix_string(value)

    mapping: dict[str, str] = {
        "FileHash-MD5": f"[file:hashes.'MD5' = '{escaped}']",
        "FileHash-SHA1": f"[file:hashes.'SHA-1' = '{escaped}']",
        "FileHash-SHA256": f"[file:hashes.'SHA-256' = '{escaped}']",
        "domain": f"[domain-name:value = '{escaped}']",
        "hostname": f"[domain-name:value = '{escaped}']",
        "URL": f"[url:value = '{escaped}']",
        "URI": f"[url:value = '{escaped}']",
        "email": f"[email-addr:value = '{escaped}']",
        "IPv4": f"[ipv4-addr:value = '{escaped}']",
        "IPv6": f"[ipv6-addr:value = '{escaped}']",
        "CIDR": f"[ipv4-addr:value = '{escaped}']",
        "CVE": f"[vulnerability:name = '{escaped}']",
        "BitcoinAddress": f"[artifact:payload_bin = '{escaped}']",
        "FilePath": f"[file:name = '{escaped}']",
        "FileName": f"[file:name = '{escaped}']",
        "File": f"[file:name = '{escaped}']",
        "Mutex": f"[mutex:name = '{escaped}']",
        "WindowsRegistryKey": f"[windows-registry-key:key = '{escaped}']",
        "WindowsRegistryKeyPath": f"[windows-registry-key:key = '{escaped}']",
        "Process": f"[process:name = '{escaped}']",
    }

    if ioc_type == "YARA":
        if is_yara_rule(value):
            return PatternResult(pattern=value, pattern_type="yara", valid=True)
        hash_type = detect_file_hash(value)
        if hash_type:
            return PatternResult(
                pattern=mapping[hash_type],
                pattern_type="stix",
                valid=True,
                yara_reclassified=True,
            )
        return PatternResult(
            pattern=f"[domain-name:value = '{escaped}']",
            valid=True,
            fallback=True,
            yara_reclassified=True,
        )

    if ioc_type in mapping:
        return PatternResult(pattern=mapping[ioc_type], valid=True)

    return PatternResult(
        pattern=f"[domain-name:value = '{escaped}']",
        valid=True,
        fallback=True,
    )


def normalize_ioc_key(ioc_type: str, value: str) -> str:
    return f"{(ioc_type or '').strip().lower()}:{(value or '').strip().lower()}"


def parse_mitre_technique_id(attack_id: str) -> str | None:
    text = (attack_id or "").strip()
    if re.match(r"^T\d{4}(?:\.\d{3})?$", text):
        return text
    return None
