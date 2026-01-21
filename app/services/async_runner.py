import asyncio
import os
import logging

from sqlalchemy.exc import OperationalError

from app.services.postgres_job_store import PostgresJobStore

logger = logging.getLogger(__name__)


def mock_sgen_execution(config: dict) -> dict:
    """
    Temporary mock execution logic.

    This will be replaced by real sgen execution or sgen-worker.
    """
    return {
        "message": "mock execution completed",
        "input_config": config,
    }


class AsyncJobRunner:
    def __init__(self, poll_interval_seconds: float = 0.5):
        self.poll_interval_seconds = poll_interval_seconds
        self.worker_id = os.getenv("CONTROLLER_WORKER_ID", "controller-local")
        self._store = PostgresJobStore()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def _wait_for_db(self) -> None:
        """
        Block startup until the database is reachable AND
        the jobs table exists.

        This prevents startup crashes in fresh environments.
        """
        logger.info("Waiting for database and schema to become available...")

        while True:
            try:
                with self._store._get_raw_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_name = 'jobs'
                            """
                        )
                        if cur.fetchone():
                            logger.info("Database and schema are available")
                            return

                await asyncio.sleep(1.0)

            except Exception:
                await asyncio.sleep(1.0)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return

        self._stop.clear()

        # NEW: wait for DB before starting execution loop
        await self._wait_for_db()

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        logger.info(
            "AsyncJobRunner started",
            extra={"worker_id": self.worker_id},
        )

        while not self._stop.is_set():
            try:
                job = self._store.claim_next_pending_job(
                    worker_id=self.worker_id
                )

                if not job:
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                if job.mode == "mock":
                    try:
                        result = mock_sgen_execution(job.payload)
                        self._store.set_job_completed(
                            job.job_id,
                            result=result,
                        )
                    except Exception as exc:
                        self._store.set_job_failed(
                            job.job_id,
                            error={"message": str(exc)},
                        )
                else:
                    # Until sgen-worker exists, fail fast for live jobs
                    self._store.set_job_failed(
                        job.job_id,
                        error={
                            "message": (
                                "live execution not implemented "
                                "(waiting for sgen-worker)"
                            )
                        },
                    )

            except Exception as exc:
                logger.exception(
                    "Runner loop error",
                    extra={"error": str(exc)},
                )
                await asyncio.sleep(1.0)

        logger.info(
            "AsyncJobRunner stopped",
            extra={"worker_id": self.worker_id},
        )
