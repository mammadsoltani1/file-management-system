from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_email_verification_token
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepo


class EmailVerificationTokenInvalidError(Exception):
    """raised when the email verification token is missing, expired, wrong or already used"""


class EmailVerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._token = EmailVerificationRepo(session)

    async def create_token_for_user(self, user_id: UUID) -> str | None:
        """creates a one time verification token, returns none when email is already verified"""

        user = await self._session.get(User, user_id)

        if user is None:
            raise ValueError("user was not found")
        if user.email_verified_at is not None:
            return None

        now = datetime.now(UTC)
        raw_token = generate_refresh_token()

        await self._token.invalidate_unused_for_user(user_id=user_id, at=now)

        verification_token = EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_email_verification_token(raw_token),
            expires_at=now
            + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
        )

        self._token.add(verification_token)
        await self._session.commit()
        return raw_token

    async def confirm_token(self, raw_token: str) -> User:
        now = datetime.now(UTC)
        verification_token = await self._token.get_by_token_hash_for_update(
            hash_email_verification_token(raw_token)
        )

        if verification_token is None:
            raise EmailVerificationTokenInvalidError
        if verification_token.used_at is not None:
            raise EmailVerificationTokenInvalidError

        expires_at = verification_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at <= now:
            verification_token.used_at = now
            await self._session.commit()
            raise EmailVerificationTokenInvalidError

        user = await self._session.get(User, verification_token.user_id)

        if user is None:
            raise EmailVerificationTokenInvalidError
        verification_token.used_at = now
        if user.email_verified_at is None:
            user.email_verified_at = now

        await self._session.commit()
        await self._session.refresh(user)
        return user
