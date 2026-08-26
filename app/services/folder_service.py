from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder
from app.repositories.folder_repository import FolderRepo
from app.schemas.folder import FolderCreate


class FolderAlreadyExistsError(Exception):
    """raised when a folder with the same name already exists in the same location"""


class ParentFolderNotFoundError(Exception):
    """raised when the requested parent folder is unavailable to the user"""


class FolderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._folders = FolderRepo(session)

    async def create_folder(self, *, owner_id: UUID, payload: FolderCreate) -> Folder:
        name = payload.name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("folder name is invalid")

        if payload.parent_id is not None:
            parent = await self._folders.get_for_owner(payload.parent_id, owner_id)

            if parent is None:
                raise ParentFolderNotFoundError

        folder_exists = await self._folders.exists_with_name(
            owner_id=owner_id, parent_id=payload.parent_id, name=name
        )
        if folder_exists:
            raise FolderAlreadyExistsError

        folder = Folder(owner_id=owner_id, parent_id=payload.parent_id, name=name)
        self._folders.add(folder)
        await self._session.commit()
        await self._session.refresh(folder)

        return folder

    async def list_folders(
        self, *, owner_id: UUID, parent_id: UUID | None
    ) -> list[Folder]:
        return await self._folders.list_for_parent(
            owner_id=owner_id, parent_id=parent_id
        )
