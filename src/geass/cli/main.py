# Author: Tony K. Okeke
# Date:   03.17.2024

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer
import httpx

from typing import Optional
from pathlib import Path
import time

from geass.cli import models, utils, jobs
from geass.cli.config import settings

app = typer.Typer(pretty_exceptions_show_locals=False)
job_logger = jobs.JobLogger(db_path=settings.db_path)

console = Console()
error_console = Console(stderr=True)


@app.command("video-to-audio", help="Convert a video file to an audio file")
def video_to_audio(video_path: Path, audio_path: Optional[Path] = None):
    """
    Converts a video file to an audio file using ffmpeg.

    Parameters
    ----------
    video_path : str
        The path to the video file that needs to be converted.
    audio_path : str, optional
        The path where the converted audio file should be saved. If not provided, the audio file is saved in the same
        location as the video file with an .mp3 extension.
    """

    video_path = video_path.resolve()
    if audio_path is None:
        audio_path = video_path.with_suffix(".mp3")
    # TODO show progress bar
    utils.ffmpeg_convert(video_path, audio_path)


@app.command("transcribe", help="Start a transcription job")
def transcribe(audio_paths: list[Path], num_threads: int = 4):
    """
    Initiates a transcription job for an audio file by uploading it to a transcription service.

    Parameters
    ----------
    audio_paths : list[Path]
        The path to the audio files to be transcribed.
    num_threads : int, optional
        The number of threads to use for submitting the transcription job. Default is 4.
    """

    for i, path in enumerate(audio_paths):
        audio_paths[i] = path.resolve()
        if not audio_paths[i].exists():
            raise typer.BadParameter(f"File '{audio_paths[i]}' does not exist")

    with httpx.Client(timeout=10) as client:
        for audio_path in audio_paths:
            response = client.post(
                settings.transcribe_service_url,
                headers=settings.service_headers,
                files={
                    "file": (
                        audio_path.name,
                        utils.create_file_generator(audio_path),
                        "audio/mpeg",
                    )
                },
            )

            try:
                data = utils.parse_geass_response(response)
                job = models.Job(
                    name=audio_path.name,
                    file=str(audio_path),
                    call_id=data["call_id"],
                    status=data["status"],
                    transcript=data["transcript"],
                    time_taken=data["time_taken"],
                )
                id = job_logger.save_job(job)

                if job.status == "completed":
                    console.print(f"Transcription {id:03d} complete.")
                else:
                    console.print(f"Running transcription {id:03d}")

            except Exception as e:
                error_console.print(f"[red][bold]Error:[/bold] {e}")
                continue


@app.command("list-jobs", help="List all transcription jobs")
def list_jobs(status: str = None, limit: int = 10, refresh: bool = False):
    table = Table(box=None, expand=True)
    table.add_column("ID", justify="left")
    table.add_column("Name", justify="left")
    table.add_column("Status", justify="center")
    table.add_column("Submitted", justify="center")
    table.add_column("Time Taken", justify="center")

    for job in job_logger.get_jobs(status=status, limit=limit):
        if refresh and job.status == "running":
            job = utils.get_job_status(job, settings)

        status_text = utils.status_text(job.status)
        if job.transcript is not None and job.transcript.time_taken is not None:
            time_taken = (
                f"{time.strftime('%H:%M:%S', time.gmtime(job.transcript.time_taken))}"
            )
        else:
            time_taken = "N/A"

        table.add_row(
            f"[bold cyan]{job.id:03d}[/bold cyan]",
            job.name,
            status_text,
            job.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            time_taken,
        )

    console.print(
        Panel(
            table,
            title="[bold]Jobs[/bold]",
            border_style="blue",
        )
    )


@app.command("check-status", help="Get the status of a job")
def check_status(job_id: int):
    job = job_logger.get_job(job_id)

    if job.status == "running":
        try:
            job = utils.get_job_status(job, settings)
        except ValueError as e:
            error_console.print(f"[red]{e}[/red]")
            return

    status_text = utils.status_text(job.status)
    console.print(
        f"[bold blue]Job {job_id}[/bold blue] ([blue]{job.name}[/blue]) is {status_text}"
    )

    return job


@app.command("get-transcript", help="Get the transcript from a job")
def get_transcript(
    job_id: int,
    format: models.TranscriptFormat = models.TranscriptFormat.TEXT,
    retry: bool = False,
    sleep: int = 5,
):
    try:
        job = job_logger.get_job(job_id)
    except ValueError as e:
        error_console.print(f"[red]{e}[/red]")
        return

    if job.transcript is None:
        with console.status("[blue]Fetching transcript[/blue]"):
            while True:
                try:
                    job = utils.get_job_status(job, settings)
                except ValueError:
                    error_console.print("[red]Error getting job status[/red]")
                    return

                if job.status == "complete":
                    break
                if not retry:
                    break
                console.print("Waiting for job to complete")
                time.sleep(sleep)

    transcript = job.transcript
    assert transcript is not None

    if format == models.TranscriptFormat.TEXT:
        print(transcript.text)
    elif format == models.TranscriptFormat.JSON:
        print(transcript.timestamps.model_dump_json())
    elif format == models.TranscriptFormat.SRT:
        print(transcript.srt)

    return


if __name__ == "__main__":
    app()
