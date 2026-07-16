import ipaddress
import re
from dataclasses import dataclass

import IndicatorTypes

HASH_PATTERNS = {
    "md5": re.compile(r"^[a-fA-F0-9]{32}$"),
    "sha1": re.compile(r"^[a-fA-F0-9]{40}$"),
    "sha256": re.compile(r"^[a-fA-F0-9]{64}$"),
}

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,})+$")
PULSE_ID_PATTERN = re.compile(r"^[0-9A-Za-z]{24}$")


@dataclass
class DetectionResult:
    input_value: str
    detected_type: str
    search_strategy: str
    indicator_type: object | None = None


def detect_input_type(value: str) -> DetectionResult:
    text = value.strip()

    try:
        parsed_ip = ipaddress.ip_address(text)
        indicator_type = IndicatorTypes.IPv6 if parsed_ip.version == 6 else IndicatorTypes.IPv4
        return DetectionResult(text, "ip", "indicator_details", indicator_type)
    except ValueError:
        pass

    if HASH_PATTERNS["md5"].match(text):
        return DetectionResult(text, "md5", "indicator_details", IndicatorTypes.FILE_HASH_MD5)
    if HASH_PATTERNS["sha1"].match(text):
        return DetectionResult(text, "sha1", "indicator_details", IndicatorTypes.FILE_HASH_SHA1)
    if HASH_PATTERNS["sha256"].match(text):
        return DetectionResult(text, "sha256", "indicator_details", IndicatorTypes.FILE_HASH_SHA256)
    if CVE_PATTERN.match(text):
        return DetectionResult(text, "cve", "indicator_details", IndicatorTypes.CVE)
    if URL_PATTERN.match(text):
        return DetectionResult(text, "url", "indicator_details", IndicatorTypes.URL)
    if EMAIL_PATTERN.match(text):
        return DetectionResult(text, "email", "pulse_search")
    if DOMAIN_PATTERN.match(text):
        return DetectionResult(text, "domain", "indicator_details", IndicatorTypes.DOMAIN)
    if PULSE_ID_PATTERN.match(text):
        return DetectionResult(text, "pulse_id", "pulse_lookup")
    return DetectionResult(text, "keyword", "pulse_search")
