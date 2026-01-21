from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1.jobs import router as jobs_router
from app.services.async_runner import AsyncJobRunner


runner = AsyncJobRunner(poll_interval_seconds=0.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await runner.start()
    yield
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
