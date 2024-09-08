# Geass

**Command your audio transcriptions API with Geass**

![Version](https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python)
![wakapi.dev](https://img.shields.io/badge/wakapi.dev-18%20hrs%2016%20mins-168014?style=for-the-badge&logo=wakatime)

![geass demo](demo.gif)

Welcome to Geass, the ultimate tool for transcribing your audio files with ease. Just like how Lelouch commands others with his Geass, you can now command your audio transcriptions with this powerful CLI and serverless API. Let's embark on this journey together and make transcribing audio as smooth as Lelouch's plans!

## Features

- Convert video files to audio format
- Transcribe audio files using the Geass serverless API
- Check the status of transcription jobs
- Retrieve transcripts in different formats (text, JSON, SRT)
- Manage and list transcription jobs

## Prerequisites

Before using Geass, make sure you have the following:

- Python 3.10 or higher
- Poetry package manager
- Modal account (for deploying the transcription service)
- ffmpeg (for video to audio conversion)

## Installation

1. Clone the repository:

```shell
git clone git@github.com:Kabilan108/geass.git
cd geass/
```

2. Install dependencies using Poetry:

```shell
poetry shell
poetry install --with dev
```

3. Set up Modal:

```shell
python -m modal setup
```

4. [Create a secret](https://modal.com/docs/guide/secrets) in your modal account called `geass-secrets`. Take a look at [.env.template](.env.template) to see what secrets need to be defined. Use the [generate-token.sh](scripts/generate_token.sh) script to generate a value for `GEASS_SERVICE_TOKEN`.

5. Deploy the transcription service:

```shell
modal deploy geass.service.main
```

Once the service is running, set `GEASS_SERVICE_API_URL` to the fast api URL. This and `GEASS_SERVICE_TOKEN` should be set in your local environment.

6. Install the Geass CLI:

```shell
pip install -e .
```

## Usage

### Convert Vido to Audio

The modal endpoint only accepts audio files, so you need to convert videos into
mp3s first. To convert a video file to audio format, use the `video-to-audio`
command:

```shell
geass video-to-audio VIDEO_PATH [AUDIO_PATH]
```

- `VIDEO_PATH`: Path to the video file.
- `AUDIO_PATH` (optional): Path where the converted audio file should be saved. If not provided, the audio file will be saved in the same location as the video file with an .mp3 extension.

### Transcribe Audio

To start a transcription job, use the transcribe command:

```shell
geass transcribe AUDIO_PATHS [--num-threads NUM_THREADS]
```

- `AUDIO_PATHS`: Path(s) to the audio file(s) to be transcribed.
- `--num-threads` (optional): Number of threads to use for submitting the transcription job (default: 4).

### List Transcription Jobs

To list all transcription jobs, use the list-jobs command:

```shell
geass list-jobs [--status STATUS] [--limit LIMIT] [--refresh]
```

- `--status` (optional): Filter jobs by status.
- `--limit` (optional): Limit the number of jobs to display (default: 10).
- `--refresh` (optional): Refresh the status of running jobs.

### Check Job Status

To check the status of a specific transcription job, use the check-status command:

```shell
geass check-status JOB_ID
```

- `JOB_ID`: ID of the transcription job.

### Get Transcript

To retrieve the transcript of a completed job, use the get-transcript command:

```shell
geass get-transcript JOB_ID [--format FORMAT] [--retry]
```

- `JOB_ID`: ID of the transcription job.
- `--format` (optional): Format of the transcript (choices: text, json, srt; default: text).
- `--retry` (optional): Retry getting the transcript if the job is not yet complete.

### Acknowledgments

We would like to express our gratitude to the following:

- The creators of Code Geass for inspiring the name and theme of this project. All hail Lelouch!
- The open-source community for providing the tools and libraries used in this project.

Remember, with Geass, you have the power to command your audio transcriptions effortlessly. Happy transcribing!
