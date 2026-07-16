from functools import lru_cache

from app.config import get_settings
from app.services.otx_client import OTXClient
from app.services.pulse_service import PulseService


@lru_cache
def get_otx_client() -> OTXClient:
    return OTXClient(get_settings())


def get_pulse_service() -> PulseService:
    return PulseService(get_otx_client())
