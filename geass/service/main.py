# Author: Tony K. Okeke
# Date:   03.17.2024

from modal import (
    App,
    Dict,
    Image,
    Period,
    Secret,
    Volume,
    asgi_app,
    gpu,
)

import time

from .models import Job, JobStatus, Transcript
from . import config, utils

GPU_CONFIG = gpu.A10G()

base_image = Image.debian_slim(python_version="3.10").pip_install(
    "fastapi==0.108.0",
    "pydantic==2.6.0",
)
job_image = (
    Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04", add_python="3.10"
    )
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.1.2+cu118", index_url="https://download.pytorch.org/whl/cu118"
    )
    .pip_install(
        "transformers==4.36.2",
        "ffmpeg-python==0.2.0",
        "huggingface-hub==0.23.5",
        "pydantic==2.6.0",
        "optimum",
        "accelerate",
        "pandas",
    )
)

app = App("geass")  # TODO: replace with App

job_cache = Dict.from_name("geass-job-cache", create_if_missing=True)
rate_limit_dict = Dict.from_name("geass-rate-limit", create_if_missing=True)

data_volume = Volume.from_name("geass-data", create_if_missing=True)


@app.function(
    image=base_image,
    volumes={config.DATA_VOLUME: data_volume},
    secrets=[Secret.from_name("geass-secrets")],
)
@asgi_app()
def fastapi_app():
    from .api import app as api_app

    return api_app


@app.function(
    gpu=GPU_CONFIG,
    concurrency_limit=5,
    image=job_image,
    volumes={
        config.DATA_VOLUME: data_volume,
    },
    secrets=[Secret.from_name("geass-secrets")],
    timeout=10 * 60,
)
def transcribe(job: Job) -> dict:
    """Transcribe an audio file

    @param job: job to transcribe
    """

    data_volume.reload()

    config.log.info("Starting transcription for %s", job.call_id)
    job.status = JobStatus.processing
    job_cache[job.key] = job

    if not job.audio_path:
        config.log.error("No audio path for job %s", job.call_id)
        job.status = JobStatus.failed
        job_cache[job.key] = job
        return job

    try:
        pipeline = utils.load_whisper_pipeline()
        segments = utils.transcribe(pipeline, job.audio_path)
        end_time = time.time()

        fmt_chunks = []
        for chk in segments["chunks"]:
            fmt_chunks.append(
                {
                    "start": utils.to_timestamp(chk["timestamp"][0]),
                    "end": utils.to_timestamp(chk["timestamp"][1]),
                    "text": chk["text"],
                }
            )

        job.end_time = end_time
        job.status = JobStatus.completed
        job.transcript = Transcript(
            text=segments["text"],
            timestamps=fmt_chunks,
        )

        config.log.info(
            "Finished transcription %s",
            job.call_id,
        )
        config.log.debug("Job: %s", job.model_dump())
        job_cache[job.key] = job
    except Exception as e:
        config.log.error("Error transcribing %s", job.call_id, exc_info=e)
        job.status = JobStatus.failed
        job_cache[job.key] = job

    return job


@app.function(
    image=base_image,
    volumes={config.DATA_VOLUME: data_volume},
    schedule=Period(days=7),
)
def cleanup_jobs(all_jobs: bool = False):
    """Remove old jobs from the job cache and delete associated audio files"""
    data_volume.reload()

    job_count = 0
    for key, job in job_cache.items():
        if job.age > config.MAX_JOB_AGE or all_jobs:
            if job.audio_path:
                path_in_volume = job.audio_path.replace(f"{config.DATA_VOLUME}", "")
                try:
                    data_volume.remove_file(path=path_in_volume)
                    job_cache.pop(key)
                    job_count += 1
                except Exception as e:
                    config.log.error(
                        "Error removing audio file %s", path_in_volume, exc_info=e
                    )

    data_volume.commit()
    config.log.info(f"Cleaned up {job_count} old jobs")
