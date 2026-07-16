from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.exports import router as exports_router
from app.api.routes.health import router as health_router
from app.api.routes.iocs import router as iocs_router
from app.api.routes.pulses import router as pulses_router
from app.api.routes.search import router as search_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.services.export_service import ExportService

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    exporter = ExportService(Path("exports"), settings.export_retention_hours)
    exporter.cleanup_old_exports()
    yield


app = FastAPI(title="AlienVault OTX Threat Intelligence Workbench API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(search_router)
app.include_router(pulses_router)
app.include_router(iocs_router)
app.include_router(exports_router)
