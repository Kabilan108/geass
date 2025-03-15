from pathlib import Path

import typer

from geass.db import (
    DEFAULTS,
    get_cached_transcript,
    save_transcription,
    update_default,
)
from geass.models import GPU, Format
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
    use_pager: bool = typer.Option(
        False,
        "--page",
        "-p",
        help="whether to use a pager to display the results",
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
    gpu: GPU = typer.Option(
        GPU.A100,
        "--gpu",
        "-g",
        help="GPU to use for remote transcription",
    ),
    interval: float | None = typer.Option(
        None,
        "--interval",
        "-i",
        help="if provided, transcript segments will be aggregated into larger `interval` sec long segments.",
        callback=lambda v: defaults_callback("interval", v),
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
                from geass.remote import create_modal_app

                run_transcription = create_modal_app(model_name, gpu)
                results = run_transcription(to_transcribe)
                if save:
                    transcripts.extend([save_transcription(t) for t in results])
                else:
                    transcripts.extend(results)

            else:
                with whisper_context(model_name, len(to_transcribe)) as (model, adv):
                    for audio_file in to_transcribe:
                        transcript = transcribe_audio(
                            model=model, audio_file=audio_file
                        )
                        if save:
                            transcript = save_transcription(transcript)
                        transcripts.append(transcript)
                        adv()

        if use_pager:
            with cns.pager():
                print_results(transcripts, fmt=fmt, interval=interval)
        else:
            print_results(transcripts, fmt=fmt, interval=interval)

    except Exception as e:
        err_cns.print(f"Unexpected error: {e}")
        raise typer.Exit(code=1)
