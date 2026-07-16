from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    otx_api_key: str = Field(alias="OTX_API_KEY")
    otx_server: str = Field(default="https://otx.alienvault.com", alias="OTX_SERVER")
    cache_ttl_seconds: int = Field(default=600, alias="CACHE_TTL_SECONDS")
    export_retention_hours: int = Field(default=24, alias="EXPORT_RETENTION_HOURS")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    # Max pulses to resolve from a keyword/tag dump search. Bounds request fan-out
    # so a broad query does not stall behind hundreds of sequential OTX calls.
    dump_max_search_pulses: int = Field(default=25, alias="DUMP_MAX_SEARCH_PULSES")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
