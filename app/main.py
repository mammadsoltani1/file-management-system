from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="A simple file management system built with FastAPI.",
    version="0.1.0",
)


@app.get("/health")
async def check_health():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}
