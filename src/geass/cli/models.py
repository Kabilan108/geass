# Author: Tony K. Okeke
# Date:   03.17.2024

from pydantic import BaseModel, RootModel, computed_field, validator

from typing import NamedTuple, Optional
from datetime import datetime
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


class RunningJob(NamedTuple):
    call_id: str
    start_time: int


class TranscriptFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    SRT = "srt"


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
