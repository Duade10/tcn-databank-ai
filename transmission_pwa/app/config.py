from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Transmission Station AI"
    openai_api_key: str = ""
    google_service_account_file: Path = Path("service-account.json")
    data_cache_seconds: int = 300
    prefer_local_workbook: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
