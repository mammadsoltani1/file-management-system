from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stored_file import StoredFile


class FileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, stored_file: StoredFile) -> None:
        self._session.add(stored_file)

    async def list_for_owner(
        self, owner_id: UUID, folder_id: UUID | None
    ) -> list[StoredFile]:
        folder_condition = (
            StoredFile.folder_id.is_(None)
            if folder_id is None
            else StoredFile.folder_id == folder_id
        )

        statement = (
            select(StoredFile)
            .where(StoredFile.owner_id == owner_id, folder_condition)
            .order_by(StoredFile.original_filename.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_for_owner(self, file_id: UUID, owner_id: UUID) -> StoredFile | None:
        statement = select(StoredFile).where(
            StoredFile.id == file_id, StoredFile.owner_id == owner_id
        )

        result = await self._session.scalars(statement)
        return result.one_or_none()
