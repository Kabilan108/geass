from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from time import time

import modal
from pydantic import BaseModel

from geass.models import GPU, Segment, Transcript
from geass.utils import get_audio_duration

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


class Request(BaseModel):
    path: Path
    bytes: bytes
    duration: str


def create_modal_app(model_name: str, gpu: GPU = GPU.A100):
    app = modal.App("geass-cli")

    @app.function(
        gpu=gpu.value,
        image=image,
        serialized=True,
        volumes={"/models": modal.Volume.from_name("geass-models")},
    )
    def transcribe_audio_file(request: Request) -> dict:
        """Process a single audio file"""
        from faster_whisper import WhisperModel

        tic = time()
        buffer = BytesIO(request.bytes)
        model = WhisperModel(model_name)
        segments, _ = model.transcribe(buffer)

        return Transcript(
            duration=request.duration,
            file_path=request.path,
            segments=[Segment(**asdict(s)) for s in segments],
            start_time=tic,
        ).model_dump()

    def run_transcription(audio_paths: list[Path]) -> Transcript:
        def prepare_request(audio_path: Path) -> Request:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            duration = get_audio_duration(audio_path)
            return Request(path=audio_path, bytes=audio_bytes, duration=duration)

        requests = list(map(prepare_request, audio_paths))

        with app.run():
            results = transcribe_audio_file.map(requests)
            # results = transcribe_audio_files.remote(requests, model_name)
            return [Transcript(**r) for r in results]

    return run_transcription
