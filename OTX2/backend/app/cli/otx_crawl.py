from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.config import get_settings
from app.core.logging import configure_logging
from app.crawler.runner import CrawlConfig, run_crawl
from app.services.otx_client import OTXClient


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        prog="otx-crawl",
        description="Crawl public AlienVault OTX pulses and store locally as JSONL with resume support.",
    )
    parser.add_argument("--mode", choices=["full", "update"], default="full", help="Full crawl or incremental update.")
    parser.add_argument("--out", default="data/otx_pulses.jsonl", help="Append-only JSONL output path.")
    parser.add_argument("--seen-ids", default="data/seen_ids.txt", help="One pulse_id per line (dedupe).")
    parser.add_argument("--checkpoint", default="data/checkpoint.json", help="Resume checkpoint file.")
    parser.add_argument("--errors", default="data/otx_pulses.errors.jsonl", help="Error JSONL output path.")

    parser.add_argument("--page-limit", type=int, default=50, help="Pulses per discovery page.")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page number (when no checkpoint).")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between HTTP calls (seconds).")
    parser.add_argument("--max-retries", type=int, default=5, help="Max retries per pulse.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit number of pages (testing).")
    parser.add_argument(
        "--update-seen-streak-stop",
        type=int,
        default=250,
        help="Update mode: stop after this many already-seen IDs in a row.",
    )

    args = parser.parse_args(argv)

    settings = get_settings()
    otx = OTXClient(settings)

    cfg = CrawlConfig(
        mode=args.mode,
        page_limit=args.page_limit,
        start_page=args.start_page,
        delay_seconds=args.delay,
        max_retries=args.max_retries,
        max_pages=args.max_pages,
        update_seen_streak_stop=args.update_seen_streak_stop,
        out_path=Path(args.out),
        seen_ids_path=Path(args.seen_ids),
        checkpoint_path=Path(args.checkpoint),
        errors_path=Path(args.errors),
    )

    stats = run_crawl(otx, cfg)
    logger.info("Crawl finished: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

