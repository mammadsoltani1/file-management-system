from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.auth_session import AuthSession
from app.repositories.auth_session_repository import AuthSessionRepo


class RefreshTokenInvalidError(Exception):
    """raised when a refresh token is invalid, expired or revoked"""


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._auth_sessions = AuthSessionRepo(session)

    async def create_refresh_session(
        self, user_id: UUID, user_agent: str | None, ip_address: str | None
    ) -> str:
        raw_token = generate_refresh_token()
        now = datetime.now(UTC)
        auth_session = AuthSession(
            user_id=user_id,
            token=hash_refresh_token(raw_token),
            family_id=uuid4(),
            created_at=now,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        await self._auth_sessions.add(auth_session)
        await self._session.commit()
        return raw_token

    async def rotate_refresh_session(
        self, raw_token: str, user_agent: str | None, ip_address: str | None
    ) -> tuple[UUID, str]:
        now = datetime.now(UTC)
        current = await self._auth_sessions.get_by_token_hash_for_update(
            hash_refresh_token(raw_token)
        )

        if current is None:
            raise RefreshTokenInvalidError

        if current.revoked_at is not None:
            if current.revoked_reason == "rotated":
                await self._auth_sessions.revoke_family(
                    family_id=current.family_id, reason="reused detected", at=now
                )
                await self._session.commit()
            raise RefreshTokenInvalidError

        expires_at = current.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < now:
            await self._auth_sessions.revoke(
                auth_session=current, reason="expired", at=now
            )
            await self._session.commit()
            raise RefreshTokenInvalidError

        successor_token = generate_refresh_token()
        successor = AuthSession(
            user_id=current.user_id,
            token=hash_refresh_token(successor_token),
            family_id=current.family_id,
            rotated_from_id=current.id,
            created_at=now,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        await self._auth_sessions.revoke(auth_session=current, reason="rotated", at=now)

        await self._auth_sessions.add(successor)
        await self._session.commit()

        return current.user_id, successor_token

    async def revoke_refresh_session(self, raw_token: str) -> None:
        current = await self._auth_sessions.get_by_token_hash_for_update(
            hash_refresh_token(raw_token)
        )

        if current is None or current.revoked_at is not None:
            return

        await self._auth_sessions.revoke(
            auth_session=current, reason="logout", at=datetime.now(UTC)
        )
        await self._session.commit()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self._auth_sessions.revoke_all_for_user(
            user_id=user_id, reason="logout", at=datetime.now(UTC)
        )
        await self._session.commit()
