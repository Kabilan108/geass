# Author: Tony K. Okeke
# Date:   03.17.2024

from modal import (
    Dict,
    Image,
    Period,
    Secret,
    Stub,
    Volume,
    asgi_app,
    gpu,
)

import time

from . import config, utils

GPU_CONFIG = gpu.T4()
logger = config.logger

model_volume = Volume.from_name("geass-models", create_if_missing=True)
data_volume = Volume.from_name("geass-data", create_if_missing=True)

api_image = Image.debian_slim(python_version="3.10").pip_install(
    "fastapi==0.108.0",
    "pydantic==2.6.0",
    "loguru==0.7.2",
)
whisper_image = (
    Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04", add_python="3.10"
    )
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.1.2+cu118", index_url="https://download.pytorch.org/whl/cu118"
    )
    .pip_install(
        "transformers==4.36.2",
        "loguru==0.7.2",
        "ffmpeg-python==0.2.0",
        "optimum",
        "accelerate",
        "pandas",
    )
)

stub = Stub("geass")
stub.jobs = Dict.new()


@stub.function(
    image=api_image,
    volumes={config.DATA_DIR: data_volume},
    secrets=[Secret.from_name("geass-secrets")],
)
@asgi_app()
def fastapi_app():
    from .api import app

    return app


@stub.function(
    gpu=GPU_CONFIG,
    image=whisper_image,
    volumes={
        config.MODEL_DIR: model_volume,
        config.DATA_DIR: data_volume,
    },
    secrets=[Secret.from_name("geass-secrets")],
    timeout=10 * 60,
)
def transcribe(audiofile: str) -> dict:
    """Transcribe an audio file

    @param audiofile: path to audio file. must be a mp3 file stored in the data volume
    """

    data_volume.reload()

    logger.info(f"Starting transcription job for {audiofile}")

    pipeline = utils.load_whisper_pipeline()
    start_time = time.time()
    segments = utils.transcribe(pipeline, audiofile)
    end_time = time.time()

    logger.info(
        f"Finished transcription job for {audiofile} in {end_time - start_time} seconds"
    )

    for i, chk in enumerate(segments["chunks"]):
        segments["chunks"][i] = {
            "start": utils.to_timestamp(chk["timestamp"][0]),
            "end": utils.to_timestamp(chk["timestamp"][1]),
            "text": chk["text"],
        }

    return {
        "transcript": {
            "text": segments["text"],
            "timestamps": segments["chunks"],
        },
        "time_taken": end_time - start_time,
    }


@stub.function(
    volumes={config.DATA_DIR: data_volume},
    secrets=[Secret.from_name("geass-secrets")],
    schedule=Period(days=7),
)
def data_cleanup():
    """Clean up the data volume"""
    data_volume.reload()
    data_volume.rmtree()
