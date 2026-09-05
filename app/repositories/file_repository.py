from uuid import UUID

from sqlalchemy import func, select
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
            .where(
                StoredFile.owner_id == owner_id,
                folder_condition,
                StoredFile.deleted_at.is_(None),
            )
            .order_by(StoredFile.name.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_for_owner(self, file_id: UUID, owner_id: UUID) -> StoredFile | None:
        statement = select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.owner_id == owner_id,
            StoredFile.deleted_at.is_(None),
        )

        result = await self._session.scalars(statement)
        return result.one_or_none()

    async def delete(self, stored_file: StoredFile) -> None:
        await self._session.delete(stored_file)

    async def list_for_folder_ids(
        self, owner_id: UUID, folder_ids: list[UUID]
    ) -> list[StoredFile]:
        if not folder_ids:
            return []

        statement = (
            select(StoredFile)
            .where(
                StoredFile.owner_id == owner_id,
                StoredFile.folder_id.in_(folder_ids),
                StoredFile.deleted_at.is_(None),
            )
            .order_by(StoredFile.created_at.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def exists_with_name(
        self,
        owner_id: UUID,
        folder_id: UUID | None,
        name: str,
        exclude_file_id: UUID | None = None,
    ) -> bool:
        folder_condition = (
            StoredFile.folder_id.is_(None)
            if folder_id is None
            else StoredFile.folder_id == folder_id
        )

        statement = select(StoredFile).where(
            StoredFile.owner_id == owner_id,
            folder_condition,
            StoredFile.name == name,
            StoredFile.deleted_at.is_(None),
        )

        if exclude_file_id is not None:
            statement = statement.where(StoredFile.id != exclude_file_id)

        result = await self._session.scalars(statement)
        return result.first() is not None

    async def count_for_folder(self, owner_id: UUID, folder_id: UUID | None) -> int:
        folder_condition = (
            StoredFile.folder_id.is_(None)
            if folder_id is None
            else StoredFile.folder_id == folder_id
        )

        statement = (
            select(func.count())
            .select_from(StoredFile)
            .where(
                StoredFile.owner_id == owner_id,
                folder_condition,
                StoredFile.deleted_at.is_(None),
            )
        )

        result = await self._session.scalar(statement)
        return int(result) if result is not None else 0

    async def list_for_folder_page(
        self, folder_id: UUID | None, owner_id: UUID, offset: int, limit: int
    ) -> list[StoredFile]:
        if limit <= 0:
            return []

        folder_condition = (
            StoredFile.folder_id.is_(None)
            if folder_id is None
            else StoredFile.folder_id == folder_id
        )

        statement = (
            select(StoredFile)
            .where(
                StoredFile.owner_id == owner_id,
                folder_condition,
                StoredFile.deleted_at.is_(None),
            )
            .order_by(StoredFile.name.asc(), StoredFile.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_by_id(self, file_id: UUID, owner_id: UUID) -> StoredFile | None:
        """fetch a file regardless of trash status"""
        statement = select(StoredFile).where(
            StoredFile.id == file_id, StoredFile.owner_id == owner_id
        )

        result = await self._session.scalars(statement)
        return result.one_or_none()

    async def list_trashed(self, owner_id: UUID) -> list[StoredFile]:
        statement = (
            select(StoredFile)
            .where(StoredFile.owner_id == owner_id, StoredFile.deleted_at.is_not(None))
            .order_by(StoredFile.deleted_at.desc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def list_for_trash_batch(
        self, owner_id: UUID, trash_batch_id: UUID
    ) -> list[StoredFile]:
        statement = select(StoredFile).where(
            StoredFile.owner_id == owner_id, StoredFile.trash_batch_id == trash_batch_id
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    @staticmethod
    def _contain_pattern(query: str) -> str:
        """escapes sql like wild cards so % _ and \\ remain literal characters in a user's query"""

        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        return f"%{escaped}%"

    async def search_for_owner(self, owner_id: UUID, query: str) -> list[StoredFile]:
        """search files by a literal case insensitive filename fragment"""
        pattern = self._contain_pattern(query)

        statement = (
            select(StoredFile)
            .where(
                StoredFile.owner_id == owner_id,
                StoredFile.deleted_at.is_(None),
                StoredFile.name.ilike(pattern, escape="\\"),
            )
            .order_by(StoredFile.name.asc(), StoredFile.id.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def list_active_for_owner_by_ids(
        self, owner_id: UUID, file_ids: list[UUID]
    ) -> list[StoredFile]:
        if not file_ids:
            return []

        statement = select(StoredFile).where(
            StoredFile.id.in_(file_ids),
            StoredFile.owner_id == owner_id,
            StoredFile.deleted_at.is_(None),
        )

        result = await self._session.scalars(statement)
        return list(result.all())
