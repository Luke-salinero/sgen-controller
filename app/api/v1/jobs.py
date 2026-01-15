from fastapi import APIRouter, HTTPException

from app.models.sgen import SGenSubmitRequest
from app.models.responses import JobCreatedResponse, JobResultResponse
from app.models.job import JobStatus
from app.services.job_store import JobStore

router = APIRouter(prefix="/jobs", tags=["jobs"])

# v0 in-memory store (process-local)
job_store = JobStore()


def mock_sgen_execution(config: dict) -> dict:
    """
    Temporary mock execution logic.

    This will be removed once workers + queues exist.
    """
    return {
        "message": "mock execution completed",
        "input_config": config,
    }


@router.post("", response_model=JobCreatedResponse)
async def create_job(req: SGenSubmitRequest):
    """
    Create a new SGen job.

    For v0:
    - mock jobs execute immediately
    - live jobs remain pending
    """
    job = job_store.create_job(req)

    if job.status == JobStatus.MOCKED:
        try:
            result = mock_sgen_execution(job.payload)
            job_store.mark_completed(job.job_id, result=result)
        except Exception as exc:
            job_store.mark_failed(
                job.job_id,
                error={"message": str(exc)},
            )

    return JobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        mode=job.mode,
    )


@router.get("/{job_id}", response_model=JobResultResponse)
async def get_job(job_id: str):
    """
    Fetch job status and result.
    """
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
