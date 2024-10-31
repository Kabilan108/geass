from pydantic_settings import BaseSettings
from pydantic import computed_field

from typing import Any
from pathlib import Path


class Settings(BaseSettings):
    GEASS_API_URL: str
    GEASS_API_TOKEN: str

    @computed_field
    def db_path(self) -> Path:
        path = Path("~/.geass.db").expanduser().resolve()
        return path

    @computed_field
    def service_status_url(self) -> str:
        return f"{self.GEASS_API_URL}/status"

    @computed_field
    def transcribe_service_url(self) -> str:
        return f"{self.GEASS_API_URL}/transcribe"

    @computed_field
    def service_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.GEASS_API_TOKEN}"}

    @computed_field
    def job_logger(self) -> Any:
        from .jobs import JobLogger

        return JobLogger(db_path=self.db_path)


settings = Settings()
