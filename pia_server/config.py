from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_path: str = "pia_metrics.db"
    rest_port: int = 8000
    mcp_port: int = 8001
    collection_interval_seconds: float = 5.0
    collector_type: Literal["mock", "real"] = "mock"
    temp_unit: Literal["F", "C"] = "F"
    log_level: str = "INFO"


settings = Settings()
