from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobCreatedResponse(BaseModel):
    """
    Returned immediately after a job is accepted by sgen-controller.
    """

    job_id: str
    status: JobStatus = Field(..., description="initial job status")
    mode: str = Field(..., description="mock or live")


class JobResultResponse(BaseModel):
    """
    Returned when querying job status.
    """

    job_id: str
    status: JobStatus
    mode: str

    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
