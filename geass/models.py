from enum import StrEnum
from pathlib import Path
from time import time

from pydantic import BaseModel, Field, computed_field, field_serializer


class GPU(StrEnum):
    T4 = "T4"
    L4 = "L4"
    A10G = "A10G"
    A100 = "A100"
    H100 = "H100"


class Format(StrEnum):
    JSON = "json"
    TEXT = "text"
    SRT = "srt"


class Segment(BaseModel):
    start: float
    end: float
    text: str
    no_speech_prob: float | None = None

    @computed_field
    @property
    def srt(self) -> str:
        f = format_srt_ts
        return f"{f(self.start)} --> {f(self.end)}\n{self.text.strip()}\n"


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
    def srt(self) -> str:
        return "\n".join(s.srt for s in self.segments).strip()

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


def format_srt_ts(timestamp):
    milliseconds = int((timestamp % 1) * 1000)
    seconds = int(timestamp % 60)
    minutes = int((timestamp // 60) % 60)
    hours = int(timestamp // 3600)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
