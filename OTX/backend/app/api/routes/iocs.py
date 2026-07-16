from fastapi import APIRouter, Depends

from app.config import get_settings
from app.core.exceptions import to_http_exception
from app.dependencies import get_pulse_service
from app.models.schemas import IOCDumpRequest, IOCDumpResponse
from app.services.ioc_dumper import IOCDumperService
from app.services.pulse_service import PulseService

router = APIRouter(prefix="/api/iocs", tags=["iocs"])


def get_ioc_dumper(pulse_service: PulseService = Depends(get_pulse_service)) -> IOCDumperService:
    return IOCDumperService(pulse_service)


@router.post("/dump", response_model=IOCDumpResponse)
def dump_iocs(
    payload: IOCDumpRequest,
    dumper: IOCDumperService = Depends(get_ioc_dumper),
) -> IOCDumpResponse:
    try:
        iocs, stats, pulses_processed, pulse_contexts = dumper.dump(
            pulse_ids=payload.pulse_ids,
            search_query=payload.search_query,
            tags=payload.tags,
            type_filter=payload.type_filter,
            max_search_pulses=get_settings().dump_max_search_pulses,
        )
        return IOCDumpResponse(iocs=iocs, stats=stats, pulses_processed=pulses_processed, pulse_contexts=pulse_contexts)
    except Exception as exc:
        raise to_http_exception(exc)
