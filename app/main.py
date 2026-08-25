from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="A simple file management system built with FastAPI.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def check_health() -> dict[str, str]:
    return {"status": "healthy", "environment": settings.ENVIRONMENT}
