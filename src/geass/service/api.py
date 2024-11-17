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

import time

from geass.service.main import (
    data_volume,
    transcribe,
    cleanup_jobs,
    job_cache,
    rate_limit_dict,
)
from geass.service.config import (
    log,
    RATE_LIMIT,
    RATE_LIMIT_WINDOW,
    GEASS_API_TOKEN,
    GEASS_ADMIN_TOKEN,
)
from geass.service.utils import save_file, generate_job_key
from geass.service.schema import APIResponse, Job, JobStatus


app = FastAPI()
auth_scheme = HTTPBearer()


def verify_token(token: HTTPAuthorizationCredentials, admin_only: bool = False):
    if admin_only:
        valid_tokens = [GEASS_ADMIN_TOKEN]
    else:
        valid_tokens = [GEASS_API_TOKEN, GEASS_ADMIN_TOKEN]

    if token.credentials not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def rate_limit(request: Request):
    client_ip = request.client.host
    current_time = int(time.time())

    # get request timestamps for I
    requests = rate_limit_dict.get(client_ip, [])

    # remove requests outside of time window
    requests = [req for req in requests if req > current_time - RATE_LIMIT_WINDOW]

    if len(requests) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    requests.append(current_time)
    rate_limit_dict[client_ip] = requests


@app.post("/transcribe")
async def transcribe_job(
    file: UploadFile = File(...),
    request: Request = Request,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """Start transcription job"""
    verify_token(token)
    rate_limit(request)

    file_content = await file.read()
    job_key = generate_job_key(file_content)
    await file.seek(0)

    existing_job = job_cache.get(job_key, None)

    if existing_job:
        if existing_job.status == JobStatus.completed:
            log.info("Found completed job %s", existing_job.call_id)
            return APIResponse(
                data={
                    "call_id": existing_job.call_id,
                    "status": existing_job.status,
                    "transcript": existing_job.transcript,
                    "time_taken": existing_job.time_taken,
                },
                message="Transcription completed",
            )
        elif existing_job.status in [JobStatus.processing, JobStatus.pending]:
            log.info("Found in-progress job %s", existing_job.call_id)
            return APIResponse(
                data={
                    "call_id": existing_job.call_id,
                    "status": existing_job.status,
                },
                message="Transcription in progress",
            )
        elif existing_job.status == JobStatus.failed:
            log.info("Found failed job %s", existing_job.call_id)
            job_cache.delete(job_key)
            pass
        else:
            log.error("Unknown job status %s", existing_job.status)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown job status {existing_job.status}",
            )

    new_job = Job(key=job_key)
    new_job.audio_path = save_file(file, new_job.call_id)
    data_volume.commit()

    job_cache.put(job_key, new_job)

    log.info("Adding job %s to queue", new_job.call_id)
    transcribe.spawn(job=new_job)

    return {"call_id": new_job.call_id}


@app.get("/status/{call_id}")
async def poll_status(
    call_id: str, token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    """Check status of a running job"""
    verify_token(token)

    # look up job in the cache
    job = next((j for j in job_cache.values() if j.call_id == call_id), None)
    if not job:
        return APIResponse(
            message=f"Job with call_id {call_id} not found",
        )

    response = {
        "call_id": job.call_id,
        "status": job.status,
        "time_taken": job.time_taken,
        "transcript": job.transcript,
    }

    if job.status == JobStatus.failed:
        return APIResponse(
            data=response,
            error=job.error,
        )
    else:
        return APIResponse(
            data=response,
            message="Transcription in progress",
        )


@app.get("/jobs")
async def list_jobs(token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """List all jobs"""
    verify_token(token, admin_only=True)

    return APIResponse(
        data=list(job_cache.values()),
        message="Retrieved job cache",
    )


@app.get("/reset")
async def reset(token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """Reset the job cache"""
    verify_token(token, admin_only=True)

    cleanup_jobs.spawn(all_jobs=True)

    return APIResponse(message="Job cache reset")
