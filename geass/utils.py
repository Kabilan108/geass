import io
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from time import time

from mutagen import File
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from geass.models import Format, Segment, Transcript, format_duration

cns = Console()
err_cns = Console(stderr=True, style="red")


def get_audio_duration(path: Path) -> float | None:
    try:
        audio = File(path)
        return format_duration(audio.info.length if audio.info else None)
    except Exception as e:
        err_cns.print(f"[yellow]Warning: failed to check duration for {path}: {e}")
        return None


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


def transcribe_audio(
    audio_file: Path,
    model,
) -> Transcript:
    """Transcribe audio data using WhisperModel."""
    buffer = io.BytesIO(audio_file.read_bytes())
    tic = time()
    segments, _ = model.transcribe(buffer)
    return Transcript(
        duration=get_audio_duration(audio_file),
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
