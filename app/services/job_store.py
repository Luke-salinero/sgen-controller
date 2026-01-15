from typing import Dict
from datetime import datetime
import threading

from app.models.job import Job, JobStatus
from app.models.sgen import SGenSubmitRequest


class JobStore:
    """
    In-memory job store (v0).

    This is the single owner of job lifecycle mutations.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self, req: SGenSubmitRequest) -> Job:
        """
        Create a new job in PENDING (or MOCKED) state.
        """
        with self._lock:
            job = Job(
                mode=req.mode,
                payload=req.config,
                status=(
                    JobStatus.MOCKED
                    if req.mode == "mock"
                    else JobStatus.PENDING
                ),
            )
            self._jobs[job.job_id] = job
            return job

    def get_job(self, job_id: str) -> Job:
        """
        Retrieve a job by ID.
        """
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job {job_id} not found")
        return job

    def mark_running(self, job_id: str, worker_id: str | None = None) -> Job:
        """
        Mark a job as running.
        """
        with self._lock:
            job = self.get_job(job_id)
            job.mark_running(worker_id=worker_id)
            return job

    def mark_completed(self, job_id: str, result: dict) -> Job:
        """
        Mark a job as completed.
        """
        with self._lock:
            job = self.get_job(job_id)
            job.mark_completed(result=result)
            return job

    def mark_failed(self, job_id: str, error: dict) -> Job:
        """
        Mark a job as failed.
        """
        with self._lock:
            job = self.get_job(job_id)
            job.mark_failed(error=error)
            return job

    def mark_cancelled(self, job_id: str) -> Job:
        """
        Cancel a job.
        """
        with self._lock:
            job = self.get_job(job_id)
            job.mark_cancelled()
            return job
