# Author: Tony K. Okeke
# Date:   03.17.2024

import os

from .logger import create_logger

log = create_logger(__name__)

GEASS_ADMIN_TOKEN = os.environ.get("GEASS_ADMIN_TOKEN", "")
GEASS_API_TOKEN = os.environ.get("GEASS_API_TOKEN", "")

RATE_LIMIT = int(os.environ.get("RATE_LIMIT", 100))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", 60))

MAX_JOB_AGE = int(os.environ.get("MAX_JOB_AGE", 60 * 60 * 24 * 5))  # 5 days

DATA_VOLUME = "/data"
UPLOADS_DIR = f"{DATA_VOLUME}/uploads"
MODEL_DIR = f"{DATA_VOLUME}/models"
WHISPER_MODEL = "openai/whisper-large-v3"
