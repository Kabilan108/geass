import io
import json
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
        length = audio.info.length if audio.info else None
    except Exception as e:
        err_cns.print(f"[yellow]Warning: failed to check duration for {path}: {e}")
        length = None
    return format_duration(length)


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
    results, _ = model.transcribe(buffer)
    return Transcript(
        duration=get_audio_duration(audio_file),
        file_path=audio_file,
        segments=[Segment(**asdict(s)) for s in results],
        start_time=tic,
    )


def print_transcripts_text(ts: list[Transcript], srt: bool = False) -> None:
    for t in ts:
        cns.print(f"""\
<transcript file_name='{t.file_path.name}' duration='{t.duration}' wall_time='{t.wall_time}'>
{t.srt if srt else t.text}
</transcript>
""")


def print_transcripts_json(ts: list[Transcript]) -> None:
    json_list = [t.model_dump() for t in ts]
    cns.print_json(json.dumps(json_list, indent=2))


def print_results(transcripts: list[Transcript], fmt: Format, interval: float | None):
    """Print the results of the transcription."""

    if interval is not None:
        for t in transcripts:
            t.segments = aggregate_segments(t.segments, interval)

    def _print_results():
        if fmt == Format.JSON:
            print_transcripts_json(transcripts)
        elif fmt == Format.TEXT:
            print_transcripts_text(transcripts)
        elif fmt == Format.SRT:
            print_transcripts_text(transcripts, True)

    _print_results()


def aggregate_segments(segments: list[Segment], interval: float) -> list[Segment]:
    """Aggregate segments into larger segments based on a time interval.

    Args:
        segments (list[Segment]): List of segments to aggregate.
        interval (int): Time interval in seconds to aggregate segments.

    Returns:
        list[Segment]: Aggregated list of segments.
    """
    ss = sorted(segments, key=lambda s: s.start)
    nss: list[Segment] = [ss[0]]
    i = 0
    for s in ss[1:]:
        if s.end - nss[i].start < interval:
            nss[i].end = s.end
            nss[i].text += s.text
            continue
        nss[i].no_speech_prob = None
        nss.append(s)
        i += 1
    return nss
