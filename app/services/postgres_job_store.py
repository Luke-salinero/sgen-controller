from contextlib import contextmanager
import json

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models.job import Job, JobStatus
from app.models.sgen import SGenSubmitRequest


class PostgresJobStore:
    """
    Postgres-backed JobStore.

    This is the authoritative store for async execution.
    """

    @contextmanager
    def _get_raw_connection(self):
        conn = engine.raw_connection()
        try:
            yield conn
        finally:
            conn.close()

    def create_job(self, config: SGenSubmitRequest, mode: str = "live") -> Job:
        payload = config.model_dump()

        job = Job(
            mode=mode,
            payload=payload,
            status=JobStatus.PENDING.value,
        )

        with SessionLocal() as session:
            session.execute(
                text("""
                INSERT INTO jobs (
                    job_id, mode, status, payload,
                    created_at, updated_at
                ) VALUES (
                    :job_id, :mode, :status, :payload,
                    NOW(), NOW()
                )
                """),
                {
                    "job_id": job.job_id,
                    "mode": job.mode,
                    "status": job.status,
                    "payload": json.dumps(payload),
                },
            )
            session.commit()

        return job

    def get_job(self, job_id: str) -> Job:
        with SessionLocal() as session:
            row = session.execute(
                text("SELECT * FROM jobs WHERE job_id = :job_id"),
                {"job_id": job_id},
            ).mappings().first()

            if not row:
                raise KeyError(job_id)

            return Job(**row)

    def claim_next_pending_job(self, worker_id: str) -> Job | None:
        with SessionLocal() as session:
            with session.begin():
                row = session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = :running,
                      worker_id = :worker_id,
                      started_at = COALESCE(started_at, NOW()),
                      updated_at = NOW()
                    WHERE job_id = (
                      SELECT job_id
                      FROM jobs
                      WHERE status = :pending
                      ORDER BY created_at ASC
                      LIMIT 1
                      FOR UPDATE SKIP LOCKED
                    )
                    RETURNING *
                    """),
                    {
                        "pending": JobStatus.PENDING.value,
                        "running": JobStatus.RUNNING.value,
                        "worker_id": worker_id,
                    },
                ).mappings().first()

                if not row:
                    return None

                return Job(**row)

    def set_job_completed(self, job_id: str, result: dict) -> Job:
        with SessionLocal() as session:
            with session.begin():
                row = session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = :completed,
                      result = :result,
                      finished_at = NOW(),
                      updated_at = NOW()
                    WHERE job_id = :job_id
                    RETURNING *
                    """),
                    {
                        "job_id": job_id,
                        "completed": JobStatus.COMPLETED.value,
                        "result": json.dumps(result),
                    },
                ).mappings().first()

                if not row:
                    raise KeyError(job_id)

                return Job(**row)

    def set_job_failed(self, job_id: str, error: dict) -> Job:
        with SessionLocal() as session:
            with session.begin():
                row = session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = :failed,
                      error = :error,
                      finished_at = NOW(),
                      updated_at = NOW()
                    WHERE job_id = :job_id
                    RETURNING *
                    """),
                    {
                        "job_id": job_id,
                        "failed": JobStatus.FAILED.value,
                        "error": json.dumps(error),
                    },
                ).mappings().first()

                if not row:
                    raise KeyError(job_id)

                return Job(**row)
