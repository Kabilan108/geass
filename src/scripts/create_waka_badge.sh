#!/bin/bash

current_dir=$(basename $(pwd))

if [ $current_dir != "geass" ]; then
    echo "This script must be run from the root of the geass project"
    exit 1
fi

if [ -z $WAKAPI_API_KEY ]; then
    echo "WAKAPI_API_KEY is not set"
    exit 1
fi

echo "[INFO] Fetching coding time from wakapi.dev"
total_seconds=$(
    curl -s -X GET -H "Authorization: Basic $(echo -n $WAKAPI_API_KEY | base64)" \
    "https://wakapi.dev/api/summary?interval=all_time&project=geass" | \
    jq '.projects[0].total')

hours=$((total_seconds / 3600))
minutes=$((total_seconds % 3600 / 60))

formatted_time=$(printf "%d hrs %02d mins" $hours $minutes | sed 's/ /%20/g')

readme_contents=$(cat README.md)

modified_contents=$(echo "$readme_contents" | \
    sed "s/\([0-9]\+\%20hrs\%20[0-9]\+\%20mins\)/$formatted_time/")

echo "[INFO] Updating README.md with new coding time"
echo "$modified_contents" > README.md
