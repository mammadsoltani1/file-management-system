from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_session import AuthSession


class AuthSessionRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, auth_session: AuthSession) -> None:
        self._session.add(auth_session)

    async def get_by_token_hash_for_update(self, token_hash: str) -> AuthSession | None:
        """lock a session during refresh token rotation"""
        statement = (
            select(AuthSession).where(AuthSession.token == token_hash).with_for_update()
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke(
        self, auth_session: AuthSession, reason: str, at: datetime
    ) -> None:
        if auth_session.revoked_at is not None:
            return

        auth_session.revoked_at = at
        auth_session.revoked_reason = reason

    async def revoke_family(self, family_id: UUID, reason: str, at: datetime) -> None:
        statement = (
            update(AuthSession)
            .where(
                AuthSession.family_id == family_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=at, revoked_reason=reason)
        )

        await self._session.execute(statement)

    async def revoke_all_for_user(
        self, user_id: UUID, reason: str, at: datetime
    ) -> None:
        statement = (
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=at, revoked_reason=reason)
        )

        await self._session.execute(statement)
