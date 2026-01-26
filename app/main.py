from contextlib import asynccontextmanager
from fastapi import FastAPI
import os

from app.api.v1.jobs import router as jobs_router
from app.services.async_runner import AsyncJobRunner


def get_runner() -> AsyncJobRunner | None:
    """
    Only run the AsyncJobRunner in mock mode.
    In live mode, workers exclusively execute jobs.
    """
    if os.getenv("SGEN_MODE", "mock") == "mock":
        return AsyncJobRunner()
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner = get_runner()

    if runner:
        await runner.start()

    yield

    if runner:
        await runner.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="sgen-controller",
        description="Control plane for SGen job scheduling and lifecycle management",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(jobs_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
