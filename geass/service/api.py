# Author: Tony K. Okeke
# Date:   03.17.2024

from fastapi import (
    Depends,
    File,
    FastAPI,
    HTTPException,
    UploadFile,
    Request,
    status,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from typing import NamedTuple
import time
import os

from .main import data_volume, transcribe, stub
from .config import logger
from . import utils


MAX_JOB_AGE_SECS = 10 * 60

app = FastAPI()
auth_scheme = HTTPBearer()

RATE_LIMIT = int(os.environ["RATE_LIMIT"])
RATE_LIMIT_WINDOW = int(os.environ["RATE_LIMIT_WINDOW"])
GEASS_SERVICE_TOKEN = os.environ["GEASS_SERVICE_TOKEN"]


class RunningJob(NamedTuple):
    call_id: str
    start_time: int


def rate_limit(request: Request):
    client_ip = request.client.host
    current_time = int(time.time())

    # get request timestamps for IP
    requests = stub.rate_limit_dict.get(client_ip, [])

    # remove requests outside of time window
    requests = [req for req in requests if req > current_time - RATE_LIMIT_WINDOW]

    if len(requests) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    requests.append(current_time)
    stub.rate_limit_dict[client_ip] = requests


@app.post("/transcribe")
async def transcribe_job(
    file: UploadFile = File(...),
    request: Request = Request,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """Start transcription job"""
    rate_limit(request)

    path, filename = utils.save_file(file)
    data_volume.commit()

    if token.credentials != os.environ["GEASS_SERVICE_TOKEN"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = int(time.time())
    job_key = f"{filename}-{now}"

    try:
        job = stub.jobs[job_key]

        if isinstance(job, RunningJob) and (now - job.start_time) < MAX_JOB_AGE_SECS:
            call_id = job.call_id
            logger.info(
                f"Found existing, unexpired job for {filename}. Returning call_id {call_id}."
            )
            return {"call_id": call_id}
    except KeyError:
        pass

    call = transcribe.spawn(audiofile=path)
    stub.jobs[job_key] = RunningJob(
        call_id=call.object_id,
        start_time=now,
    )

    return {"call_id": call.object_id}


@app.get("/status/{call_id}")
async def poll_status(call_id: str):
    """Check status of a running job"""

    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)

    try:
        res = function_call.get(timeout=0.1)
    except TimeoutError:
        return {"status": "running"}
    except Exception as exc:
        if exc.args:
            inner_exc = exc.args[0]
            if "HTTPError 403" in inner_exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied on transcription job",
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unknown error processing job",
        )

    logger.info(f"Completed transcription for {call_id}")

    return {
        "status": "complete",
        "transcript": res["transcript"],
        "time_taken": res["time_taken"],
    }
