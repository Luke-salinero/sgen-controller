from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """
    Authoritative job lifecycle states.

    These are owned by the control plane (sgen-controller),
    not by workers or the gateway.
    """

    PENDING = "pending"      # accepted, not yet running
    RUNNING = "running"      # claimed by a worker
    COMPLETED = "completed"  # finished successfully
    FAILED = "failed"        # finished with error
    CANCELLED = "cancelled"  # explicitly cancelled
    MOCKED = "mocked"        # mock execution (v0 only)


class Job(BaseModel):
    """
    Core Job model owned by sgen-controller.

    This is the source of truth for job state.
    """

    job_id: str = Field(default_factory=lambda: str(uuid4()))

    # execution mode
    mode: str = Field(..., description="mock or live")

    # lifecycle
    status: JobStatus = Field(default=JobStatus.PENDING)

    # payload (opaque to controller; interpreted by executor)
    payload: Dict[str, Any]

    # results
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    # timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # worker metadata (future)
    worker_id: Optional[str] = None

    def mark_running(self, worker_id: Optional[str] = None) -> None:
        self.status = JobStatus.RUNNING
        self.worker_id = worker_id
        self.started_at = datetime.utcnow()
        self.updated_at = self.started_at

    def mark_completed(self, result: Dict[str, Any]) -> None:
        self.status = JobStatus.COMPLETED
        self.result = result
        self.finished_at = datetime.utcnow()
        self.updated_at = self.finished_at

    def mark_failed(self, error: Dict[str, Any]) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.finished_at = datetime.utcnow()
        self.updated_at = self.finished_at

    def mark_cancelled(self) -> None:
        self.status = JobStatus.CANCELLED
        self.finished_at = datetime.utcnow()
        self.updated_at = self.finished_at
