import io
from contextlib import contextmanager
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from time import time

from mutagen import File
from pydantic import BaseModel, Field, computed_field, field_serializer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

cns = Console()
err_cns = Console(stderr=True, style="red")


class Format(StrEnum):
    TEXT = "text"
    JSON = "json"


class Segment(BaseModel):
    start: float
    end: float
    text: str
    no_speech_prob: float


class Transcript(BaseModel):
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
    def duration(self) -> str:
        sec = get_audio_duration(self.file_path)
        return format_duration(sec)

    @computed_field
    @property
    def wall_time(self) -> str:
        return format_duration(self.end_time - self.start_time)


def get_audio_duration(path: Path) -> float | None:
    try:
        audio = File(path)
        return audio.info.length if audio.info else None
    except Exception as e:
        err_cns.print(f"[yellow]Warning: failed to check duration for {path}: {e}")
        return None


def format_duration(sec: float | None) -> str:
    if sec is None:
        return "Unknown"

    hours, remainder = divmod(int(sec), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def list_available_models() -> list[str]:
    """Get available Whisper models."""
    return [
        "tiny.en",
        "tiny",
        "base.en",
        "base",
        "small.en",
        "small",
        "medium.en",
        "medium",
        "large-v1",
        "large-v2",
        "large-v3",
        "large",
        "distil-large-v2",
        "distil-medium.en",
        "distil-small.en",
        "distil-large-v3",
        "large-v3-turbo",
        "turbo",
    ]


def get_model_params():
    """Get parameters for WhisperModel"""
    import torch

    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"
    return {
        "device": device,
        "compute_type": compute_type,
    }


@contextmanager
def whisper_context(name: str, n: int):
    import torch
    from faster_whisper import WhisperModel

    model = WhisperModel(name, **get_model_params())

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=err_cns,
        transient=True,
    ) as pg:
        task = pg.add_task("Transcribing audio files...", total=n)
        yield model, lambda: pg.advance(task)

    del model
    torch.cuda.empty_cache()


# TODO: pass the transcript id and store it in the Transcript object
def transcribe_audio(
    audio_file: Path,
    model,
) -> Transcript:
    """Transcribe audio data using WhisperModel."""
    buffer = io.BytesIO(audio_file.read_bytes())
    tic = time()
    segments, _ = model.transcribe(buffer)
    return Transcript(
        file_path=audio_file,
        segments=[Segment(**asdict(s)) for s in segments],
        start_time=tic,
    )


def print_transcripts_text(ts: list[Transcript]) -> None:
    for t in ts:
        cns.print(f"""\
<transcript file_name='{t.file_path.name}' duration='{t.duration}' wall_time='{t.wall_time}'>
{t.text}
</transcript>
""")


def print_transcripts_json(ts: list[Transcript]) -> None:
    for t in ts:
        cns.print_json(t.model_dump_json())


def print_results(transcripts: list[Transcript], fmt: Format, pager_len: int):
    """Print the results of the transcription."""

    def _print_results():
        if fmt == Format.TEXT:
            print_transcripts_text(transcripts)
        elif fmt == Format.JSON:
            print_transcripts_json(transcripts)

    if any(len(t.text) > pager_len for t in transcripts):
        with cns.pager():
            _print_results()
    else:
        _print_results()
