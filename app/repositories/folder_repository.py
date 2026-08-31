from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder


class FolderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_owner(self, folder_id: UUID, owner_id: UUID) -> Folder | None:
        statement = select(Folder).where(
            Folder.id == folder_id, Folder.owner_id == owner_id
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def exists_with_name(
        self, *, owner_id: UUID, parent_id: UUID | None, name: str
    ) -> bool:
        statement = select(Folder).where(
            Folder.owner_id == owner_id,
            Folder.parent_id == parent_id,
            Folder.name == name,
        )

        result = await self._session.execute(statement)

        return result.scalar_one_or_none() is not None

    async def list_for_parent(
        self, *, owner_id: UUID, parent_id: UUID | None
    ) -> list[Folder]:
        statement = (
            select(Folder)
            .where(Folder.owner_id == owner_id, Folder.parent_id == parent_id)
            .order_by(Folder.name)
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
            .where(Folder.owner_id == owner_id, parent_condition)
            .order_by(Folder.name.asc())
        )

        result = await self._session.scalars(statement)
        return list(result.all())

    async def delete(self, folder: Folder) -> None:
        await self._session.delete(folder)
