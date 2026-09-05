from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.file_share import FileShare


class FileShareRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, file_share: FileShare) -> None:
        self._session.add(file_share)

    async def get_for_file_and_recipient(
        self, file_id: UUID, recipient_id: UUID
    ) -> FileShare | None:
        statement = select(FileShare).where(
            FileShare.file_id == file_id, FileShare.recipient_id == recipient_id
        )

        result = await self._session.scalars(statement)

        return result.one_or_none()

    async def get_for_owner(self, share_id: UUID, owner_id: UUID) -> FileShare | None:
        statement = select(FileShare).where(
            FileShare.id == share_id, FileShare.owner_id == owner_id
        )

        result = await self._session.scalars(statement)
        return result.one_or_none()

    async def list_for_file_owner(
        self, file_id: UUID, owner_id: UUID
    ) -> list[FileShare]:
        statement = (
            select(FileShare)
            .where(FileShare.file_id == file_id, FileShare.owner_id == owner_id)
            .options(selectinload(FileShare.recipient))
            .order_by(FileShare.created_at.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def list_received_by_user(self, recipient_id: UUID) -> list[FileShare]:
        statement = (
            select(FileShare)
            .where(FileShare.recipient_id == recipient_id)
            .options(selectinload(FileShare.file))
            .order_by(FileShare.created_at.desc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def delete(self, file_share: FileShare) -> None:
        await self._session.delete(file_share)
