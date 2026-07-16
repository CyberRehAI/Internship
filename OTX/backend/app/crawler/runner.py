from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.crawler.discovery import OTXPulseDiscovery
from app.crawler.parser import normalize_indicators, normalize_pulse_full
from app.crawler.rate_limit import backoff_sleep, sleep_seconds
from app.crawler.storage.jsonl_store import JsonlPulseStore
from app.crawler.types import CrawlCheckpoint, CrawlErrorRecord, Mode
from app.crawler.utils import atomic_write_json, append_jsonl, utc_now_iso
from app.services.otx_client import OTXClient

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    mode: Mode = "full"
    page_limit: int = 50
    start_page: int = 1
    delay_seconds: float = 1.0
    max_retries: int = 5
    max_pages: int | None = None
    # Update-mode stop condition: if we see this many already-seen pulse IDs in a row, stop.
    update_seen_streak_stop: int = 250

    out_path: Path = Path("data/otx_pulses.jsonl")
    seen_ids_path: Path = Path("data/seen_ids.txt")
    checkpoint_path: Path = Path("data/checkpoint.json")
    errors_path: Path = Path("data/otx_pulses.errors.jsonl")


def _load_checkpoint(path: Path) -> CrawlCheckpoint:
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data  # type: ignore[return-value]
    except Exception:
        logger.exception("Failed to load checkpoint; starting fresh")
    return {}


def _write_checkpoint(path: Path, ckpt: CrawlCheckpoint) -> None:
    atomic_write_json(path, ckpt)  # atomic replace


def _write_error(path: Path, err: CrawlErrorRecord) -> None:
    append_jsonl(path, err)


def run_crawl(otx: OTXClient, cfg: CrawlConfig) -> dict[str, object]:
    start_ts = time.time()

    ckpt = _load_checkpoint(cfg.checkpoint_path)
    if ckpt.get("mode") and ckpt.get("mode") != cfg.mode:
        logger.warning("Checkpoint mode=%s differs from run mode=%s; continuing with run mode", ckpt.get("mode"), cfg.mode)

    last_page = int(ckpt.get("last_page") or cfg.start_page)
    last_index_in_page = int(ckpt.get("last_index_in_page") or 0)

    written = int(ckpt.get("written_pulses") or 0)
    skipped = int(ckpt.get("skipped_pulses") or 0)
    failed = int(ckpt.get("failed_pulses") or 0)

    store = JsonlPulseStore(out_path=cfg.out_path, seen_ids_path=cfg.seen_ids_path)
    discovery = OTXPulseDiscovery(otx)

    update_seen_streak = 0
    pages_processed = 0

    current_page = last_page
    while True:
        if cfg.max_pages is not None and pages_processed >= cfg.max_pages:
            break

        page_data = discovery.fetch_page(page=current_page, limit=cfg.page_limit)
        pages_processed += 1
        results = page_data.results
        if not results:
            logger.info("Discovery exhausted (empty results). Stopping.")
            break

        # Resume within a page.
        start_idx = last_index_in_page if current_page == last_page else 0

        logger.info("Page %s (results=%s) starting at index %s", current_page, len(results), start_idx)

        for idx in range(start_idx, len(results)):
            item = results[idx]
            pulse_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(pulse_id, str) or not pulse_id:
                continue

            # Update-mode early stop: once we hit a long streak of already-seen IDs, assume we've caught up.
            if cfg.mode == "update" and update_seen_streak >= cfg.update_seen_streak_stop:
                logger.info("Update mode stop: seen streak reached %s", cfg.update_seen_streak_stop)
                return _final_stats(cfg, start_ts, written, skipped, failed)

            if store.has_pulse(pulse_id):
                skipped += 1
                update_seen_streak += 1
                # Save progress after every pulse (even skips).
                ckpt = {
                    "last_page": current_page,
                    "last_index_in_page": idx + 1,
                    "written_pulses": written,
                    "skipped_pulses": skipped,
                    "failed_pulses": failed,
                    "mode": cfg.mode,
                    "updated_at": utc_now_iso(),
                }
                _write_checkpoint(cfg.checkpoint_path, ckpt)
                continue

            update_seen_streak = 0

            # Fetch + parse with retries.
            attempt = 0
            while True:
                attempt += 1
                try:
                    sleep_seconds(cfg.delay_seconds)
                    pulse = otx.get_pulse_details(pulse_id)
                    sleep_seconds(cfg.delay_seconds)
                    indicators = otx.get_pulse_indicators(pulse_id, limit=1000)

                    record = normalize_pulse_full(pulse)
                    record["iocs"] = normalize_indicators(indicators)

                    store.append_pulse(record)
                    written += 1

                    ckpt = {
                        "last_page": current_page,
                        "last_index_in_page": idx + 1,
                        "written_pulses": written,
                        "skipped_pulses": skipped,
                        "failed_pulses": failed,
                        "mode": cfg.mode,
                        "updated_at": utc_now_iso(),
                    }
                    _write_checkpoint(cfg.checkpoint_path, ckpt)
                    break
                except Exception as exc:
                    err: CrawlErrorRecord = {
                        "pulse_id": pulse_id,
                        "page": current_page,
                        "index_in_page": idx,
                        "attempt": attempt,
                        "error": type(exc).__name__,
                        "message": str(exc),
                        "timestamp": utc_now_iso(),
                        "endpoint": "pulse_details+indicators",
                    }
                    _write_error(cfg.errors_path, err)

                    if attempt >= cfg.max_retries:
                        failed += 1
                        ckpt = {
                            "last_page": current_page,
                            "last_index_in_page": idx + 1,
                            "written_pulses": written,
                            "skipped_pulses": skipped,
                            "failed_pulses": failed,
                            "mode": cfg.mode,
                            "updated_at": utc_now_iso(),
                        }
                        _write_checkpoint(cfg.checkpoint_path, ckpt)
                        logger.exception("Pulse failed after retries: %s", pulse_id)
                        break

                    logger.warning("Retrying pulse %s (attempt %s/%s): %s", pulse_id, attempt, cfg.max_retries, exc)
                    backoff_sleep(attempt=attempt)

        # Move to next page.
        if not page_data.next_url:
            logger.info("Discovery exhausted (no next link). Stopping.")
            break

        current_page += 1
        last_page = current_page
        last_index_in_page = 0

    return _final_stats(cfg, start_ts, written, skipped, failed)


def _final_stats(cfg: CrawlConfig, start_ts: float, written: int, skipped: int, failed: int) -> dict[str, object]:
    elapsed = max(0.001, time.time() - start_ts)
    rate = written / elapsed
    out_size = cfg.out_path.stat().st_size if cfg.out_path.exists() else 0
    stats = {
        "written_pulses": written,
        "skipped_pulses": skipped,
        "failed_pulses": failed,
        "runtime_seconds": elapsed,
        "avg_pulses_per_second": rate,
        "output_bytes": out_size,
        "output_path": str(cfg.out_path),
    }
    logger.info(
        "Run summary: written=%s skipped=%s failed=%s runtime=%.1fs rate=%.3f/s size=%s bytes",
        written,
        skipped,
        failed,
        elapsed,
        rate,
        out_size,
    )
    return stats

