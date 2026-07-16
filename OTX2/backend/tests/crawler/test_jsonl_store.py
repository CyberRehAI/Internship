from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.crawler.storage.jsonl_store import JsonlPulseStore


class JsonlPulseStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.out_path = base / "pulses.jsonl"
        self.seen_ids_path = base / "seen_ids.txt"
        self.store = JsonlPulseStore(out_path=self.out_path, seen_ids_path=self.seen_ids_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_mark_seen_without_jsonl_write(self) -> None:
        self.store.mark_seen("abc123")
        self.assertTrue(self.store.has_pulse("abc123"))
        self.assertEqual(self.seen_ids_path.read_text(encoding="utf-8").strip(), "abc123")
        self.assertFalse(self.out_path.exists())

    def test_mark_seen_is_idempotent(self) -> None:
        self.store.mark_seen("abc123")
        self.store.mark_seen("abc123")
        lines = [line for line in self.seen_ids_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(lines, ["abc123"])

    def test_append_pulse_writes_jsonl_and_marks_seen(self) -> None:
        record = {"pulse_id": "pulse1", "title": "Test", "iocs": [{"indicator": "1.2.3.4", "type": "IPv4"}]}
        self.store.append_pulse(record)
        self.assertTrue(self.store.has_pulse("pulse1"))
        self.assertIn("pulse1", self.out_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
