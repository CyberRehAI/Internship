from fastapi import APIRouter, Depends, Query

from app.core.exceptions import to_http_exception
from app.dependencies import get_pulse_service
from app.services.pulse_service import PulseService

router = APIRouter(prefix="/api/pulses", tags=["pulses"])


@router.get("/search")
def search_pulses(
    q: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
    pulse_service: PulseService = Depends(get_pulse_service),
) -> dict:
    try:
        pulses = pulse_service.search(q, limit=limit)
        return {"results": pulses, "count": len(pulses)}
    except Exception as exc:
        raise to_http_exception(exc)


@router.get("/{pulse_id}")
def get_pulse_details(pulse_id: str, pulse_service: PulseService = Depends(get_pulse_service)) -> dict:
    try:
        return pulse_service.get_details(pulse_id)
    except Exception as exc:
        raise to_http_exception(exc)


@router.get("/{pulse_id}/indicators")
def get_pulse_indicators(
    pulse_id: str,
    limit: int = Query(1000, ge=1, le=5000),
    pulse_service: PulseService = Depends(get_pulse_service),
) -> dict:
    try:
        indicators = pulse_service.get_indicators(pulse_id, limit=limit)
        return {"results": indicators, "count": len(indicators)}
    except Exception as exc:
        raise to_http_exception(exc)
