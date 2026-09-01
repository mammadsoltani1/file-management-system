from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerificationToken


class EmailVerificationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, verification_token: EmailVerificationToken) -> None:
        self._session.add(verification_token)

    async def invalidate_unused_for_user(self, user_id: UUID, at: datetime) -> None:
        """a user should only have one useable verification token at a time"""

        statement = (
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=at)
        )
        await self._session.execute(statement)

    async def get_by_token_hash_for_update(
        self, token_hash: str
    ) -> EmailVerificationToken | None:
        statement = (
            select(EmailVerificationToken)
            .where(EmailVerificationToken.token_hash == token_hash)
            .with_for_update()
        )

        result = await self._session.scalars(statement)
        return result.one_or_none()
