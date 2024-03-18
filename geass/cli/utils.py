# Author: Tony K. Okeke
# Date:   03.17.2024

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)
import ffmpeg
import httpx

from typing import Generator
from pathlib import Path
import os

from . import models

CONFIG_FILE = Path("~/.geass.json").expanduser()


def ffmpeg_convert(input_path: str, output_path: str):
    ffmpeg.input(input_path).output(output_path).run()


def status_text(status: str) -> str:
    return (
        f"[bold green]{status} [green]:heavy_check_mark:"
        if status == "complete"
        else f"[bold yellow]{status}[red]:exclamation:"
    )


def get_job_status(job: models.Job, config: models.Settings) -> models.Job:
    with httpx.Client() as client:
        response = client.get(f"{config.service_status_url}/{job.call_id}")

    if response.status_code == 200:
        job.status = response.json()["status"]
        if job.status == "complete":
            transcript = response.json()["transcript"]
            job.transcript = models.Transcript(
                text=transcript["text"],
                timestamps=[models.TimeStamp(**c) for c in transcript["timestamps"]],
            )
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
