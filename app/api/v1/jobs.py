from fastapi import APIRouter, HTTPException

from app.models.responses import JobCreatedResponse, JobResultResponse
from app.services.postgres_job_store import PostgresJobStore
from app.models.requests import CreateJobRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])

job_store = PostgresJobStore()


@router.post("", response_model=JobCreatedResponse)
async def create_job(req: CreateJobRequest):
    job = job_store.create_job(req.config)

    return JobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        mode=job.mode,
    )


@router.get("/{job_id}", response_model=JobResultResponse)
async def get_job(job_id: str):
    try:
        job = job_store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        mode=job.mode,
        result=job.result,
        error=job.error,
    )
