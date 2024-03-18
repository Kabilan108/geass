# Geass

### Command your audio transcriptions API with Geass

## Installation

```shell
# clone repository
git clone git@github.com:Kabilan108/geass.git
cd geass/

# install dependencies
poetry shell
poetry install --with dev

# set up modal
python -m modal setup

# deploy changes to the transcription service
modal deploy geass.service.main

# install geass CLI
pip install -e .
```
