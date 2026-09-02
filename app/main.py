from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import get_db_session
from app.services.email_verification_service import (
    EmailVerificationService,
    EmailVerificationTokenInvalidError,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="A simple file management system built with FastAPI.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def check_health() -> dict[str, str]:
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


def _verification_page(title: str, message: str) -> str:
    return f"""\
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family: Arial, sans-serif; text-align: center; padding: 4rem;">
    <h1>{title}</h1>
    <p>{message}</p>
</body>
</html>"""


@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email(
    token: str, session: AsyncSession = Depends(get_db_session)
) -> str:
    try:
        await EmailVerificationService(session).confirm_token(token)
    except EmailVerificationTokenInvalidError:
        return _verification_page(
            "verification failed",
            "this verification link is invalid, expired or already used. "
            "please request a new one.",
        )

    return _verification_page(
        "email verified",
        "your email address has been verified, you can close this tab.",
    )
