# Author: Tony K. Okeke
# Date:   03.17.2024

from time import gmtime, strftime
import hashlib
import shutil
import os

from . import config


def generate_job_key(file_content):
    return hashlib.md5(file_content).hexdigest()


def repo_id_to_model_path(repo_id):
    return os.path.join(config.MODEL_DIR, "--".join(repo_id.split("/")))


def download_whisper_model(data_volume=None):
    """Download the Whisper model from HuggingFace"""

    from huggingface_hub import snapshot_download

    path = snapshot_download(
        repo_id=config.WHISPER_MODEL,
        repo_type="model",
        local_dir=repo_id_to_model_path(config.WHISPER_MODEL),
    )
    if data_volume:
        data_volume.commit()
    return path


def load_whisper_pipeline(data_volume=None):
    """Load the Whisper ASR pipeline"""

    from transformers import pipeline, logging
    import torch

    logging.set_verbosity_error()

    model_path = repo_id_to_model_path(config.WHISPER_MODEL)
    if not os.path.exists(model_path):
        model_path = download_whisper_model(data_volume)

    gpu = torch.cuda.is_available()
    device = "cuda" if gpu else "cpu"

    pipeline = pipeline(
        "automatic-speech-recognition",
        model=model_path,
        torch_dtype=torch.float16 if gpu else torch.int8,
        device=device,
    )

    return pipeline


def to_timestamp(seconds: int) -> str:
    return strftime("%H:%M:%S", gmtime(seconds))


def transcribe(pipe, audiofile):
    """Transcribe an audio file"""

    import torch

    segments = pipe(
        audiofile,
        chunk_length_s=30,
        batch_size=12,
        return_timestamps=True,
        generate_kwargs={
            "task": "transcribe",
            "language": "en",
        },
    )
    torch.cuda.empty_cache()

    return segments


def save_file(file, job_id):
    """Write uploaded file to disk"""

    if not os.path.exists(config.UPLOADS_DIR):
        os.makedirs(config.UPLOADS_DIR)

    path = f"{config.UPLOADS_DIR}/{job_id}.{file.filename.split('.')[-1]}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return path
