from pathlib import Path

import typer

from geass.db import (
    DEFAULTS,
    get_cached_transcript,
    save_transcription,
    update_default,
)
from geass.models import Format
from geass.remote import run_remote_transcription
from geass.utils import (
    cns,
    err_cns,
    list_available_models,
    print_results,
    transcribe_audio,
    whisper_context,
)

cli = typer.Typer(pretty_exceptions_show_locals=False)

models = list_available_models()


def defaults_callback(key: str, value: str) -> str:
    if value != DEFAULTS[key]:
        update_default(key, value)
    return value


def files_callback(paths: list[Path]) -> list[Path]:
    resolved = []
    for p in paths:
        if not p.exists():
            raise typer.BadParameter(f"File {p} does not exist.")
        resolved.append(p.resolve())
    return resolved


@cli.command("list-models", help="list available transcription models.")
def list_models():
    """list available transcription models.
    pass these model ids to the -m flag of the `transcribe` command
    """
    cns.print("\n".join(models))


@cli.command("transcribe", help="transcribe audio file.")
def transcribe(
    audio_files: list[Path] = typer.Argument(
        ...,
        help="one or more audio file paths to transcribe",
        callback=files_callback,
    ),
    fmt: Format = typer.Option(
        Format.TEXT,
        "--format",
        "-f",
        help="output format for the transcription",
    ),
    model_name: str = typer.Option(
        DEFAULTS["model_name"],
        "--model",
        "-m",
        help="transcription model to use. run `geass list-models` to see available models.",
        callback=lambda v: defaults_callback("model_name", v),
    ),
    pager_len: int = typer.Option(
        DEFAULTS["pager_len"],
        "--pager-len",
        "-p",
        help="length of text to display before switching to pager mode",
        callback=lambda v: defaults_callback("pager_len", v),
    ),
    save: bool = typer.Option(
        False,
        "--save",
        "-s",
        help="save the transcript to a file",
    ),
    remote: bool = typer.Option(
        False,
        "--remote",
        "-r",
        help="transcribe audio file using remote server",
    ),
):
    if model_name not in models:
        raise typer.BadParameter(
            f"model '{model_name}' not found. the following models are available: {', '.join(models)}"
        )

    try:
        transcripts = []
        to_transcribe = []

        for audio_file in audio_files:
            cached_transcript = get_cached_transcript(audio_file)
            if cached_transcript:
                transcripts.append(cached_transcript)
            else:
                to_transcribe.append(audio_file)

        if to_transcribe:
            if remote:
                transcripts = run_remote_transcription(to_transcribe, model_name)

            else:
                with whisper_context(model_name, len(to_transcribe)) as (
                    model,
                    advance,
                ):
                    for audio_file in to_transcribe:
                        transcript = transcribe_audio(
                            model=model, audio_file=audio_file
                        )
                        if save:
                            transcript = save_transcription(transcript)
                        transcripts.append(transcript)
                        advance()

        print_results(transcripts, fmt=fmt, pager_len=pager_len)
    except Exception as e:
        err_cns.print(f"Unexpected error: {e}")
        raise typer.Exit(code=1)
