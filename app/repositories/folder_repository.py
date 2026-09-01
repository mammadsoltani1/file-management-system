from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder


class FolderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_owner(self, folder_id: UUID, owner_id: UUID) -> Folder | None:
        statement = select(Folder).where(
            Folder.id == folder_id,
            Folder.owner_id == owner_id,
            Folder.deleted_at.is_(None),
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def exists_with_name(
        self,
        *,
        owner_id: UUID,
        parent_id: UUID | None,
        name: str,
        exclude_folder_id: UUID | None = None,
    ) -> bool:
        parent_condition = (
            Folder.parent_id.is_(None)
            if parent_id is None
            else Folder.parent_id == parent_id
        )

        statement = select(Folder).where(
            Folder.owner_id == owner_id,
            parent_condition,
            Folder.name == name,
            Folder.deleted_at.is_(None),
        )

        if exclude_folder_id is not None:
            statement = statement.where(Folder.id != exclude_folder_id)

        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_for_parent(
        self, *, owner_id: UUID, parent_id: UUID | None
    ) -> list[Folder]:
        parent_condition = (
            Folder.parent_id.is_(None)
            if parent_id is None
            else Folder.parent_id == parent_id
        )

        statement = (
            select(Folder)
            .where(
                Folder.owner_id == owner_id,
                parent_condition,
                Folder.deleted_at.is_(None),
            )
            .order_by(Folder.name.asc(), Folder.id.asc())
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    def add(self, folder: Folder) -> None:
        self._session.add(folder)

    async def list_for_owner(
        self, owner_id: UUID, parent_id: UUID | None
    ) -> list[Folder]:
        parent_condition = (
            Folder.parent_id.is_(None)
            if parent_id is None
            else Folder.parent_id == parent_id
        )

        statement = (
            select(Folder)
            .where(
                Folder.owner_id == owner_id,
                parent_condition,
                Folder.deleted_at.is_(None),
            )
            .order_by(Folder.name.asc(), Folder.id.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def delete(self, folder: Folder) -> None:
        await self._session.delete(folder)

    async def count_for_parent(self, owner_id: UUID, parent_id: UUID | None) -> int:
        parent_condition = (
            Folder.parent_id.is_(None)
            if parent_id is None
            else Folder.parent_id == parent_id
        )

        statement = (
            select(func.count())
            .select_from(Folder)
            .where(
                Folder.owner_id == owner_id,
                parent_condition,
                Folder.deleted_at.is_(None),
            )
        )

        result = await self._session.scalar(statement)
        return int(result) if result is not None else 0

    async def list_for_parent_page(
        self, owner_id: UUID, parent_id: UUID | None, offset: int, limit: int
    ) -> list[Folder]:
        if limit <= 0:
            return []

        parent_condition = (
            Folder.parent_id.is_(None)
            if parent_id is None
            else Folder.parent_id == parent_id
        )

        statement = (
            select(Folder)
            .where(
                Folder.owner_id == owner_id,
                parent_condition,
                Folder.deleted_at.is_(None),
            )
            .order_by(Folder.name.asc(), Folder.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_by_id(self, folder_id: UUID, owner_id: UUID) -> Folder | None:
        """fetch a folder regardless of trash status"""
        statement = select(Folder).where(
            Folder.id == folder_id, Folder.owner_id == owner_id
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_trashed(self, owner_id: UUID) -> list[Folder]:
        statement = (
            select(Folder)
            .where(Folder.owner_id == owner_id, Folder.deleted_at.is_not(None))
            .order_by(Folder.deleted_at.desc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def list_for_trash_batch(
        self, owner_id: UUID, trash_batch_id: UUID
    ) -> list[Folder]:
        statement = select(Folder).where(
            Folder.owner_id == owner_id, Folder.trash_batch_id == trash_batch_id
        )

        result = await self._session.scalars(statement)
        return list(result.all())
