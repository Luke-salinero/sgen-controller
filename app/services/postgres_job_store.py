from contextlib import contextmanager
import json
from typing import Dict, Any

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models.job import Job, JobStatus
from app.models.sgen import SGenSubmitRequest

def ensure_schema():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            payload JSONB NOT NULL,
            result JSONB,
            error JSONB,
            worker_id TEXT,
            api_key_owner TEXT,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
        """))

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

    def create_job(self, config: Dict[str, Any], subject_id: str, mode: str = "live") -> Job:
        payload = config

        job = Job(
            mode=mode,
            payload=payload,
            status=JobStatus.CREATED.value,
        )

        with SessionLocal() as session:
            session.execute(
                text("""
                INSERT INTO jobs (
                    job_id, mode, status, payload, api_key_owner
                    created_at, updated_at
                ) VALUES (
                    :job_id, :mode, :status, :payload, :api_key_owner
                    NOW(), NOW()
                )
                """),
                {
                    "job_id": job.job_id,
                    "mode": job.mode,
                    "status": job.status,
                    "payload": json.dumps(payload),
                    "api_key_owner": subject_id,
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
        
    
    def claim_next_created_job(self) -> Job | None:
        with SessionLocal() as session:
            with session.begin():
                row = session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = :pending,
                      updated_at = NOW()
                    WHERE job_id = (
                      SELECT job_id
                      FROM jobs
                      WHERE status = :created
                      ORDER BY created_at ASC
                      LIMIT 1
                      FOR UPDATE SKIP LOCKED
                    )
                    RETURNING *
                    """),
                    {
                        "pending": JobStatus.PENDING.value,
                        "created": JobStatus.CREATED.value,
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
