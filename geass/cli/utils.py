# Author: Tony K. Okeke
# Date:   03.17.2024

from tqdm import tqdm
import ffmpeg

from time import gmtime, strftime
from typing import Generator
from pathlib import Path
import os

from . import models

CONFIG_FILE = Path("~/.geass.json").expanduser()


def load_config() -> models.GeassOpts:
    if not CONFIG_FILE.exists():
        opts = models.GeassOpts()
        save_config(opts)
        return opts

    with open(CONFIG_FILE, "r") as f:
        return models.GeassOpts.parse_raw(f.read())


def save_config(config: models.GeassOpts):
    with open(CONFIG_FILE, "w") as f:
        f.write(config.json())


def ffmpeg_convert(input_path: str, output_path: str):
    ffmpeg.input(input_path).output(output_path).run()


def to_timestamp(seconds: int) -> str:
    return strftime("%H:%M:%S", gmtime(seconds))


def upload_file(audio_path: Path) -> Generator[bytes, None, None]:
    with open(audio_path, "rb") as f:
        file_size = os.path.getsize(audio_path)
        chunk_size = 1024

        with tqdm(
            desc="uploading",
            total=file_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as pg:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                pg.update(len(chunk))
