from __future__ import annotations

import unittest

from app.crawler.parser import IP_INDICATOR_TYPES, normalize_indicators


class NormalizeIndicatorsTests(unittest.TestCase):
    def test_keeps_ipv4_and_ipv6(self) -> None:
        indicators = [
            {"indicator": "1.2.3.4", "type": "IPv4", "role": "c2", "description": "c2 ip"},
            {"indicator": "2001:db8::1", "type": "IPv6", "role": "", "description": "ipv6"},
        ]
        result = normalize_indicators(indicators)
        self.assertEqual(len(result), 2)
        self.assertEqual({item["type"] for item in result}, IP_INDICATOR_TYPES)
        self.assertEqual(result[0]["indicator"], "1.2.3.4")
        self.assertEqual(result[1]["indicator"], "2001:db8::1")

    def test_discards_non_ip_types(self) -> None:
        indicators = [
            {"indicator": "evil.com", "type": "domain"},
            {"indicator": "https://evil.com", "type": "URL"},
            {"indicator": "abc", "type": "FileHash-MD5"},
            {"indicator": "CVE-2024-0001", "type": "CVE"},
            {"indicator": "a@b.com", "type": "email"},
            {"indicator": "rule", "type": "YARA"},
            {"indicator": "10.0.0.0/8", "type": "CIDR"},
        ]
        self.assertEqual(normalize_indicators(indicators), [])

    def test_mixed_list_keeps_only_ip_types(self) -> None:
        indicators = [
            {"indicator": "8.8.8.8", "type": "IPv4"},
            {"indicator": "evil.com", "type": "domain"},
            {"indicator": "2001:db8::2", "type": "IPv6"},
            {"indicator": "deadbeef", "type": "FileHash-SHA256"},
        ]
        result = normalize_indicators(indicators)
        self.assertEqual(len(result), 2)
        self.assertEqual([item["indicator"] for item in result], ["8.8.8.8", "2001:db8::2"])

    def test_discards_missing_or_empty_type(self) -> None:
        indicators = [
            {"indicator": "1.2.3.4"},
            {"indicator": "5.6.7.8", "type": ""},
            {"indicator": "9.9.9.9", "type": "   "},
        ]
        self.assertEqual(normalize_indicators(indicators), [])

    def test_skips_non_dict_items(self) -> None:
        indicators = [
            "not-a-dict",
            None,
            {"indicator": "1.1.1.1", "type": "IPv4"},
        ]
        result = normalize_indicators(indicators)  # type: ignore[arg-type]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["indicator"], "1.1.1.1")


if __name__ == "__main__":
    unittest.main()
