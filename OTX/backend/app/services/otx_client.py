import logging
from typing import Any

import requests
from OTXv2 import BadRequest, InvalidAPIKey, NotFound, OTXv2
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import Settings
from app.core.exceptions import (
    OTXBadRequestError,
    OTXInvalidApiKeyError,
    OTXNotFoundError,
)
from app.services.cache import TTLCache

logger = logging.getLogger(__name__)


_POOL_SIZE = 20


class OTXClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OTXv2(api_key=settings.otx_api_key, server=settings.otx_server)
        self.cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
        self._configure_connection_pool()

    def _configure_connection_pool(self) -> None:
        session = self.client.session()
        adapter = HTTPAdapter(
            pool_connections=_POOL_SIZE,
            pool_maxsize=_POOL_SIZE,
            max_retries=Retry(
                total=5,
                status_forcelist=[429, 500, 502, 503, 504],
                backoff_factor=1,
            ),
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

    def _execute(self, fn, *args, **kwargs) -> Any:
        try:
            return fn(*args, **kwargs)
        except InvalidAPIKey as exc:
            raise OTXInvalidApiKeyError() from exc
        except NotFound as exc:
            raise OTXNotFoundError(str(exc)) from exc
        except BadRequest as exc:
            raise OTXBadRequestError(str(exc)) from exc
        except requests.RequestException as exc:
            logger.exception("Network error while requesting OTX")
            raise RuntimeError("OTX network error") from exc

    def get_user_me(self) -> dict[str, Any]:
        url = self.client.create_url("/api/v1/users/me")
        return self._execute(self.client.get, url)

    def search_pulses(self, query: str, max_results: int = 25) -> dict[str, Any]:
        return self._execute(self.client.search_pulses, query, max_results=max_results)

    def get_pulse_details(self, pulse_id: str) -> dict[str, Any]:
        cache_key = f"pulse:{pulse_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        pulse = self._execute(self.client.get_pulse_details, pulse_id)
        self.cache.set(cache_key, pulse)
        return pulse

    def get_pulse_indicators(self, pulse_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        cache_key = f"pulse-indicators:{pulse_id}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        indicators = self._execute(self.client.get_pulse_indicators, pulse_id, limit=limit)
        self.cache.set(cache_key, indicators)
        return indicators

    def get_indicator_details_full(self, indicator_type: Any, value: str) -> dict[str, Any]:
        return self._execute(self.client.get_indicator_details_full, indicator_type, value)

    def get_public_pulses_activity(self, page: int = 1, limit: int = 50) -> dict[str, Any]:
        """
        Proof-of-concept discovery helper.

        Uses the OTX v1 pulses activity feed as a paginated pulse listing.
        We intentionally keep this method thin so the crawler can iterate pages
        and stop when results are empty or `next` is missing.
        """
        url = self.client.create_url("/api/v1/pulses/activity", page=page, limit=limit)
        return self._execute(self.client.get, url)
