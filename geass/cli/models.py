# Author: Tony K. Okeke
# Date:   03.17.2024

from pydantic import BaseModel, RootModel, computed_field, validator
from pydantic_settings import BaseSettings

from typing import Any, Generator, NamedTuple, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum


class TimeStamp(BaseModel):
    start: str
    end: str
    text: str

    @validator("start", "end")
    def validate_time_format(cls, value):
        try:
            datetime.strptime(value, "%H:%M:%S")
        except ValueError:
            raise ValueError("Time must be in %H:%M:%S format")
        return value

    def __str__(self):
        return f"{self.start} ---> {self.end}\n{self.text.strip()}"


class TimeStamps(RootModel):
    root: list[TimeStamp]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, index):
        return self.root[index]


class Transcript(BaseModel):
    text: str
    timestamps: TimeStamps
    time_taken: Optional[float] = None

    @computed_field
    def srt(self) -> str:
        return "\n\n".join([str(ts) for ts in self.timestamps])


class Job(BaseModel):
    id: Optional[int] = None
    name: str
    file: str
    call_id: str
    status: str
    start_time: Optional[datetime] = None
    transcript: Optional[Transcript] = None
    # TODO: add a field for 'time_taken' -> returned from api


class RunningJob(NamedTuple):
    call_id: str
    start_time: int


class Settings(BaseSettings):
    GEASS_SERVICE_API_URL: str
    GEASS_SERVICE_TOKEN: str

    @computed_field
    def db_path(self) -> Path:
        path = Path("~/.geass.db").expanduser().resolve()
        return path

    @computed_field
    def service_status_url(self) -> str:
        return f"{self.GEASS_SERVICE_API_URL}/status"

    @computed_field
    def transcribe_service_url(self) -> str:
        return f"{self.GEASS_SERVICE_API_URL}/transcribe"

    @computed_field
    def service_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.GEASS_SERVICE_TOKEN}"}

    @computed_field
    def job_logger(self) -> Any:
        from .jobs import JobLogger

        return JobLogger(db_path=self.db_path)


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
