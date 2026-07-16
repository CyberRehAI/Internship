import time

from fastapi import APIRouter, Depends

from app.core.exceptions import to_http_exception
from app.dependencies import get_otx_client
from app.models.schemas import HealthResponse
from app.services.otx_client import OTXClient

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(otx_client: OTXClient = Depends(get_otx_client)) -> HealthResponse:
    started = time.perf_counter()
    try:
        user = otx_client.get_user_me()
        elapsed_ms = (time.perf_counter() - started) * 1000
        return HealthResponse(
            status="connected",
            otx_user=user.get("username"),
            latency_ms=round(elapsed_ms, 2),
        )
    except Exception as exc:
        raise to_http_exception(exc)
