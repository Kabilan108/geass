# Author: Tony K. Okeke
# Date:   03.17.2024

from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings

from typing import Generator, Optional
from pathlib import Path
from enum import Enum

from . import utils


class Settings(BaseSettings):
    GEASS_SERVICES_API_URL: str
    GEASS_SERVICES_API_KEY: str

    @computed_field
    def config_file(self) -> str:
        path = Path("~/.geass.json").expanduser()
        return path

    @computed_field
    def service_status_url(self) -> str:
        return f"{self.GEASS_SERVICES_API_URL}/status"

    @computed_field
    def transcribe_service_url(self) -> str:
        return f"{self.GEASS_SERVICES_API_URL}/transcribe"

    @computed_field
    def service_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.GEASS_SERVICES_API_KEY}"}

    @computed_field
    def opts(self) -> dict:
        return utils.load_config()


class Job(BaseModel):
    name: str
    url: str
    notes: Optional[dict] = {}


class GeassOpts(BaseModel):
    jobs: list[Job] = []


class TranscriptFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    SRT = "srt"


class GeneratorFile:
    def __init__(self, generator: Generator):
        self.generator = generator

    def read(self, size=-1):
        try:
            return next(self.generator)
        except StopIteration:
            return b""
