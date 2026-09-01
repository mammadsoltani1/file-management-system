import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_passwords(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hash_password: str) -> bool:
    return password_context.verify(plain_password, hash_password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expires_at}

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_refresh_token() -> str:
    """generates a secure random refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """hashes the refresh token using hmac with the application's secret key."""
    return hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=token.encode("utf-8"),
        digestmod="sha256",
    ).hexdigest()


def hash_email_verification_token(token: str) -> str:
    """hash verification tokens separately from refresh tokens"""
    payload = f"email-verification: {token}"

    return hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod="sha256",
    ).hexdigest()
