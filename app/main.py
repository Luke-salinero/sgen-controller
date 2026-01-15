from fastapi import FastAPI

from app.api.v1.jobs import router as jobs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="sgen-controller",
        description="Control plane for SGen job scheduling and lifecycle management",
        version="0.1.0",
    )

    app.include_router(jobs_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
