# Geass

CLI tool for audio transcription using `faster-whisper`. Supports local and remote
transcription (via [Modal](https://modal.com)), caching, and multiple output formats.

![PyPI](https://img.shields.io/pypi/v/geass)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)
![wakapi.dev](https://wakapi.dev/api/badge/Kabilan108/interval:any/project:geass)

## Features

- Transcribes audio files using `faster-whisper` models (e.g., `base`, `large-v3`).
- Local transcription with CPU/GPU support or remote via Modal with GPU options (T4, A100, etc.).
- Output formats: plain text, JSON, SRT.
- Aggregates segments into larger chunks with `--interval`.

## Installation

```bash
pip install geass
```

Requires Python 3.10+. For local GPU use, ensure CUDA and PyTorch are set up.

## Usage

### List Available Models

```bash
geass list-models
```

Shows all `faster-whisper` models (e.g., `tiny`, `large-v3-turbo`).

### Transcribe Audio

```bash
geass transcribe audio.wav
```

Transcribes `audio.wav` with default settings (`base` model, text output).

#### Options

- `-m, --model`: Specify model (e.g., `-m large-v3`).
- `-f, --format`: Output format (`text`, `json`, `srt`). Default: `text`.
- `-s, --save`: Save transcription to database.
- `-r, --remote`: Use Modal for remote transcription.
- `-g, --gpu`: GPU type for remote (e.g., `-g A100`). Default: `A100`.
- `-i, --interval`: Aggregate segments into intervals (e.g., `-i 10` for 10s chunks).

#### Examples

Transcribe with a specific model and JSON output:
```bash
geass transcribe audio.mp3 -m large-v2 -f json
```

Remote transcription with saving:
```bash
geass transcribe audio.wav -r -s
```

Multiple files with SRT output:
```bash
geass transcribe file1.wav file2.mp3 -f srt
```

## Database

Transcriptions are cached in `~/.geass.db`. Tables:
- `transcripts`: Stores file metadata (path, duration, timings).
- `segments`: Stores transcription segments (start, end, text).
- `cache`: Maps file hashes to transcript IDs.
- `defaults`: Stores settings (model, etc.).

## Notes

- Local GPU transcription uses `float16` on CUDA, `int8` on CPU.
- Remote transcription requires a Modal account and setup.
- The output is wrapped in XML `<transcript>` tags.
