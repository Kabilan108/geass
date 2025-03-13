from enum import StrEnum
from pathlib import Path
from time import time

from pydantic import BaseModel, Field, computed_field, field_serializer


class Format(StrEnum):
    TEXT = "text"
    JSON = "json"


class Segment(BaseModel):
    start: float
    end: float
    text: str
    no_speech_prob: float


class Transcript(BaseModel):
    duration: str
    file_path: Path
    segments: list[Segment]
    start_time: float
    end_time: float = Field(default_factory=time)

    @field_serializer("file_path")
    def serialize_path(self, v: Path) -> str:
        return str(v)

    @computed_field
    @property
    def text(self) -> str:
        return "".join(s.text for s in self.segments).strip()

    @computed_field
    @property
    def wall_time(self) -> str:
        return format_duration(self.end_time - self.start_time)


def format_duration(sec: float | None) -> str:
    if sec is None:
        return "Unknown"

    hours, remainder = divmod(int(sec), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
