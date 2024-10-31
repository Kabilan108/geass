from pydantic import BaseModel, Field, computed_field

from enum import Enum
from uuid import uuid4
import time


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Transcript(BaseModel):
    text: str
    timestamps: list[dict]


class JobData(BaseModel):
    call_id: str
    status: JobStatus
    transcript: Transcript | None = None
    time_taken: float | None = None


class APIResponse(BaseModel):
    message: str | None = None
    data: JobData | dict | list | None = None
    error: str | None = None


class Job(BaseModel):
    key: str
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    start_time: float = Field(default_factory=lambda: time.time())
    end_time: float | None = None
    audio_path: str | None = None
    status: JobStatus = JobStatus.pending
    transcript: Transcript | None = None
    error: str | None = None

    @computed_field
    def age(self) -> float:
        return time.time() - self.start_time

    @computed_field
    def time_taken(self) -> float | None:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
