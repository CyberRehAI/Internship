import argparse
import json
import sys
from datetime import datetime, timezone

from app.config import get_settings
from app.services.otx_client import OTXClient


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="otx-discovery-poc",
        description="Proof-of-concept: enumerate public OTX Pulse IDs via a paginated listing endpoint.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Pulses per page.")
    parser.add_argument("--pages", type=int, default=2, help="How many pages to fetch (PoC).")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page number.")
    parser.add_argument("--print-json", action="store_true", help="Print full response JSON for the first page.")
    args = parser.parse_args(argv)

    settings = get_settings()
    client = OTXClient(settings)

    page = args.start_page
    total_ids = 0

    for i in range(args.pages):
        resp = client.get_public_pulses_activity(page=page, limit=args.limit)
        results = resp.get("results") or []

        if i == 0 and args.print_json:
            print(json.dumps(resp, indent=2, sort_keys=True))

        ids = [item.get("id") for item in results if isinstance(item, dict) and item.get("id")]
        for pulse_id in ids:
            print(pulse_id)

        total_ids += len(ids)

        next_url = resp.get("next")
        if not results or not next_url:
            print(
                f"[{_utc_now_iso()}] stop: empty page or no next link (page={page}, discovered={total_ids})",
                file=sys.stderr,
            )
            break

        page += 1

    print(f"[{_utc_now_iso()}] done: discovered={total_ids}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

