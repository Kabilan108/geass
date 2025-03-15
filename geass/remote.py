from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from time import time

import modal
from pydantic import BaseModel

from geass.models import GPU, Segment, Transcript
from geass.utils import get_audio_duration

# TODO: add a mount to store the model so it doesn't need to be re-downloaded every time
# Issue URL: https://github.com/Kabilan108/geass/issues/2
# TODO: implement a way to spawn multiple containers to run transciption in parallel
# Issue URL: https://github.com/Kabilan108/geass/issues/1

cuda_image = "nvidia/cuda:12.6.0-cudnn-runtime-ubuntu22.04"
models_volume = modal.Volume.from_name("geass-models")
image = (
    modal.Image.from_registry(cuda_image, add_python="3.12")
    .pip_install(
        "ffmpeg-python==0.2.0",
        "pydantic==2.6.4",
        "rich==13.7.1",
        "modal>=0.73.92",
        "fastlite>=0.1.2",
        "faster-whisper>=1.1.1",
        "typer>=0.15.0",
        "mutagen>=1.47.0",
        "torch>=2.6.0",
    )
    .env({"HF_HOME": "/models"})
    .add_local_python_source("geass")
)


def create_modal_app(gpu: GPU = GPU.A100):
    app = modal.App("geass-cli")

    @app.function(
        gpu=gpu.value,
        image=image,
        serialized=True,
        volumes={"/models": modal.Volume.from_name("geass-models")},
    )
    def transcribe_audio_files(requests: list[Request], model_name: str) -> list[dict]:
        from faster_whisper import WhisperModel

        transcripts = []
        for r in requests:
            tic = time()
            buffer = BytesIO(r.bytes)
            model = WhisperModel(model_name)
            segments, _ = model.transcribe(buffer)
            transcripts.append(
                Transcript(
                    duration=r.duration,
                    file_path=r.path,
                    segments=[Segment(**asdict(s)) for s in segments],
                    start_time=tic,
                ).model_dump()
            )

        return transcripts

    def run_transcription(audio_paths: list[Path], model_name: str) -> Transcript:
        def prepare_request(audio_path: Path) -> Request:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            duration = get_audio_duration(audio_path)
            return Request(path=audio_path, bytes=audio_bytes, duration=duration)

        requests = list(map(prepare_request, audio_paths))

        with modal.enable_output():
            with app.run():
                results = transcribe_audio_files.remote(requests, model_name)
                return [Transcript(**r) for r in results]

    return run_transcription


class Request(BaseModel):
    path: Path
    bytes: bytes
    duration: str


def run_remote_transcription(
    audio_paths: list[Path], model_name: str, gpu: GPU
) -> Transcript:
    return create_modal_app(gpu)(audio_paths, model_name)
