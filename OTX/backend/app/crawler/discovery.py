from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.services.otx_client import OTXClient


@dataclass(frozen=True)
class DiscoveryPage:
    page: int
    results: list[dict[str, Any]]
    next_url: str | None


class OTXPulseDiscovery:
    """
    Enumerate public pulses using the verified listing endpoint.

    Termination condition: empty results OR missing `next` link.
    """

    def __init__(self, otx: OTXClient) -> None:
        self.otx = otx

    def fetch_page(self, page: int, limit: int) -> DiscoveryPage:
        resp = self.otx.get_public_pulses_activity(page=page, limit=limit)
        results = resp.get("results") or []
        if not isinstance(results, list):
            results = []
        next_url = resp.get("next")
        if not isinstance(next_url, str) or not next_url:
            next_url = None
        return DiscoveryPage(page=page, results=results, next_url=next_url)

    def iter_pulse_ids(
        self,
        *,
        start_page: int = 1,
        limit: int = 50,
    ) -> Iterable[tuple[int, int, str]]:
        """
        Yields tuples: (page, index_in_page, pulse_id)
        """
        page = start_page
        while True:
            page_data = self.fetch_page(page=page, limit=limit)
            if not page_data.results:
                return

            for idx, item in enumerate(page_data.results):
                if not isinstance(item, dict):
                    continue
                pulse_id = item.get("id")
                if isinstance(pulse_id, str) and pulse_id:
                    yield page, idx, pulse_id

            if not page_data.next_url:
                return

            page += 1

