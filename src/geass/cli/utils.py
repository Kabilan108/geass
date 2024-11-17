# Author: Tony K. Okeke
# Date:   03.17.2024

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
import pydantic
import ffmpeg
import httpx

from typing import Generator
from pathlib import Path
import os

from .config import Settings
from .models import Job, Transcript

CONFIG_FILE = Path("~/.geass.json").expanduser()


def ffmpeg_convert(input_path: Path, output_path: Path):
    ffmpeg.input(str(input_path)).output(str(output_path)).run()


def status_text(status: str) -> str:
    return (
        f"[bold green]{status} [green]:heavy_check_mark:"
        if status == "complete"
        else f"[bold yellow]{status}[red]:exclamation:"
    )


def get_job_status(job: Job, config: Settings) -> Job:
    with httpx.Client(
        headers=httpx.Headers({"Authorization": f"Bearer {config.GEASS_API_TOKEN}"})
    ) as client:
        response = client.get(f"{config.service_status_url}/{job.call_id}")
        res_data = response.json().get("data")
    if response.status_code == 200:
        job.status = res_data.get("status")
        try:
            if job.status == "completed":
                job.transcript = Transcript(**res_data["transcript"])
        except pydantic.ValidationError as e:
            raise ValueError(f"Transcript validation error: {e.errors()}")
        config.job_logger.update_job(job)
    else:
        raise ValueError("Error from services API")

    return job


def upload_file(audio_path: Path) -> Generator[bytes, None, None]:
    with open(audio_path, "rb") as f:
        file_size = os.path.getsize(audio_path)
        chunk_size = 1024

        pg_cols = [
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            BarColumn(bar_width=None),
            DownloadColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ]

        with Progress(*pg_cols, transient=False) as pg:
            task = pg.add_task("uploading", filename=audio_path.name, total=file_size)

            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                pg.update(task, advance=len(chunk))


class GeneratorFile:
    def __init__(self, generator: Generator):
        self.generator = generator

    def read(self, size=-1):
        try:
            return next(self.generator)
        except StopIteration:
            return b""


def create_file_generator(audio_path: Path) -> GeneratorFile:
    return GeneratorFile(upload_file(audio_path))


def parse_geass_response(response: httpx.Response) -> dict:
    res = response.json()
    data = res.get("data", {})
    error = res.get("error", "")

    if response.status_code == 200 and not error:
        return data
    else:
        raise Exception(error)
