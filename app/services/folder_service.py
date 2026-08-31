from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder
from app.repositories.file_repository import FileRepo
from app.repositories.folder_repository import FolderRepo
from app.schemas.folder import FolderCreate, FolderMove, FolderRename
from app.storage.base import StorageProvider


class FolderAlreadyExistsError(Exception):
    """raised when a folder with the same name already exists in the same location"""


class ParentFolderNotFoundError(Exception):
    """raised when the requested parent folder is unavailable to the user"""


class FolderNotFoundError(Exception):
    """raised when the requested folder does not exist or in unavailable to user"""


class FolderNotEmptyError(Exception):
    """raised when deletion is attempted on a non empty folder without recursion"""


class InvalidFolderMoveError(Exception):
    """raised when a folder is moved into itself or one of its descendants"""


class FolderService:
    def __init__(self, session: AsyncSession, storage: StorageProvider) -> None:
        self._session = session
        self._storage = storage
        self._folders = FolderRepo(session)
        self._files = FileRepo(session)

    async def create_folder(self, *, owner_id: UUID, payload: FolderCreate) -> Folder:
        name = self._validate_folder_name(payload.name)

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

    async def delete_folder(
        self, owner_id: UUID, folder_id: UUID, recursive: bool
    ) -> None:
        folder = await self._folders.get_for_owner(
            folder_id=folder_id, owner_id=owner_id
        )

        if folder is None:
            raise FolderNotFoundError

        child_folders = await self._folders.list_for_parent(
            owner_id=owner_id, parent_id=folder_id
        )

        direct_files = await self._files.list_for_owner(
            owner_id=owner_id, folder_id=folder_id
        )

        if not recursive and (child_folders or direct_files):
            raise FolderNotEmptyError

        folders_to_delete = await self._collect_folder_tree(
            owner_id=owner_id, root_folder=folder
        )
        folder_ids = [item.id for item in folders_to_delete]
        files_to_delete = await self._files.list_for_folder_ids(
            owner_id=owner_id, folder_ids=folder_ids
        )

        try:
            for stored_file in files_to_delete:
                await self._storage.delete(stored_file.storage_key)

            for stored_file in files_to_delete:
                await self._files.delete(stored_file)

            for item in reversed(folders_to_delete):
                await self._folders.delete(item)

            await self._session.commit()

        except Exception:
            await self._session.rollback()
            raise

    async def rename_folder(
        self, owner_id: UUID, folder_id: UUID, payload: FolderRename
    ) -> Folder:
        folder = await self._folders.get_for_owner(
            folder_id=folder_id, owner_id=owner_id
        )
        if folder is None:
            raise FolderNotFoundError

        name = self._validate_folder_name(payload.name)

        duplicate_exists = await self._folders.exists_with_name(
            owner_id=owner_id,
            parent_id=folder.parent_id,
            name=name,
            exclude_folder_id=folder.id,
        )

        if duplicate_exists:
            raise FolderAlreadyExistsError

        folder.name = name
        await self._session.commit()
        await self._session.refresh(folder)
        return folder

    async def move_folder(
        self, owner_id: UUID, folder_id: UUID, payload: FolderMove
    ) -> Folder:
        folder = await self._folders.get_for_owner(
            folder_id=folder_id, owner_id=owner_id
        )
        if folder is None:
            raise FolderNotFoundError

        destination_parent_id = payload.parent_id
        if destination_parent_id == folder_id:
            raise InvalidFolderMoveError

        if destination_parent_id is not None:
            destination_folder = await self._folders.get_for_owner(
                folder_id=destination_parent_id, owner_id=owner_id
            )
            if destination_folder is None:
                raise ParentFolderNotFoundError

            await self._ensure_not_moving_into_descendant(
                owner_id=owner_id, folder=folder, destination_folder=destination_folder
            )

        duplicate_exists = await self._folders.exists_with_name(
            owner_id=owner_id,
            parent_id=destination_parent_id,
            name=folder.name,
            exclude_folder_id=folder.id,
        )
        if duplicate_exists:
            raise FolderAlreadyExistsError

        folder.parent_id = destination_parent_id
        await self._session.commit()
        await self._session.refresh(folder)
        return folder

    async def _collect_folder_tree(
        self, owner_id: UUID, root_folder: Folder
    ) -> list[Folder]:
        folders: list[Folder] = []
        pending_folders = [root_folder]

        while pending_folders:
            current_folder = pending_folders.pop()
            folders.append(current_folder)

            children = await self._folders.list_for_parent(
                owner_id=owner_id, parent_id=current_folder.id
            )
            pending_folders.extend(children)

        return folders

    @staticmethod
    def _validate_folder_name(name: str) -> str:
        normalized = name.strip()

        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
        ):
            raise ValueError("folder name is invalid")

        return normalized

    async def _ensure_not_moving_into_descendant(
        self, owner_id: UUID, folder: Folder, destination_folder: Folder
    ) -> None:
        current_folder: Folder | None = destination_folder
        visited_folder_ids: set[UUID] = set()

        while current_folder is not None:
            if current_folder.id == folder.id:
                raise InvalidFolderMoveError
            if current_folder.id in visited_folder_ids:
                raise InvalidFolderMoveError

            visited_folder_ids.add(current_folder.id)

            if current_folder.parent_id is None:
                return

            current_folder = await self._folders.get_for_owner(
                folder_id=current_folder.parent_id, owner_id=owner_id
            )

            if current_folder is None:
                raise InvalidFolderMoveError
