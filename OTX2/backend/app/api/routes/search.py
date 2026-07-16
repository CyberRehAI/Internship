from fastapi import APIRouter, Depends, Query

from app.core.exceptions import to_http_exception
from app.dependencies import get_otx_client, get_pulse_service
from app.models.schemas import SearchResponse
from app.services.indicator_detector import detect_input_type
from app.services.otx_client import OTXClient
from app.services.pulse_service import PulseService

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def global_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
    otx_client: OTXClient = Depends(get_otx_client),
    pulse_service: PulseService = Depends(get_pulse_service),
) -> SearchResponse:
    detection = detect_input_type(q)
    indicator_result = None
    pulses: list[dict] = []

    try:
        if detection.search_strategy == "indicator_details" and detection.indicator_type is not None:
            indicator_result = otx_client.get_indicator_details_full(detection.indicator_type, detection.input_value)
            pulses = pulse_service.search(detection.input_value, limit=limit)
        elif detection.search_strategy == "pulse_lookup":
            pulse = pulse_service.get_details(detection.input_value)
            pulses = [pulse]
        else:
            pulses = pulse_service.search(detection.input_value, limit=limit)
    except Exception as exc:
        raise to_http_exception(exc)

    return SearchResponse(
        query=q,
        detected_type=detection.detected_type,
        search_strategy=detection.search_strategy,
        indicator_result=indicator_result,
        pulses=pulses,
        total_pulses=len(pulses),
    )
