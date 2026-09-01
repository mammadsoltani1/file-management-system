from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import Folder
from app.models.stored_file import StoredFile
from app.repositories.file_repository import FileRepo
from app.repositories.folder_repository import FolderRepo
from app.services.file_service import FilenameAlreadyExistsError
from app.services.folder_service import FolderAlreadyExistsError
from app.storage.base import StorageProvider


class TrashBatchNotFoundError(Exception):
    """raised when no trashed items match the requested batch for this owner"""


class TrashService:
    def __init__(self, session: AsyncSession, storage: StorageProvider) -> None:
        self._session = session
        self._storage = storage
        self._folders = FolderRepo(session)
        self._files = FileRepo(session)

    async def list_trash(
        self, *, owner_id: UUID
    ) -> tuple[list[Folder], list[StoredFile]]:
        folders = await self._folders.list_trashed(owner_id=owner_id)
        files = await self._files.list_trashed(owner_id=owner_id)
        return folders, files

    async def restore_batch(self, owner_id: UUID, trash_batch_id: UUID) -> None:
        folders = await self._folders.list_for_trash_batch(
            owner_id=owner_id, trash_batch_id=trash_batch_id
        )
        files = await self._files.list_for_trash_batch(
            owner_id=owner_id, trash_batch_id=trash_batch_id
        )

        if not folders and not files:
            raise TrashBatchNotFoundError

        restored_folder_ids = {folder.id for folder in folders}

        for folder in folders:
            parent_id = await self._resolve_restored_parent(
                owner_id, folder.parent_id, restored_folder_ids
            )

            if await self._folders.exists_with_name(
                owner_id=owner_id,
                parent_id=parent_id,
                name=folder.name,
                exclude_folder_id=folder.id,
            ):
                raise FolderAlreadyExistsError

            folder.parent_id = parent_id
            folder.deleted_at = None
            folder.trash_batch_id = None

        for stored_file in files:
            folder_id = await self._resolve_restored_parent(
                owner_id, stored_file.folder_id, restored_folder_ids
            )

            if await self._files.exists_with_name(
                owner_id, folder_id, stored_file.name, exclude_file_id=stored_file.id
            ):
                raise FilenameAlreadyExistsError

            stored_file.folder_id = folder_id
            stored_file.deleted_at = None
            stored_file.trash_batch_id = None

        await self._session.commit()

    async def _resolve_restored_parent(
        self,
        owner_id: UUID,
        parent_id: UUID | None,
        restored_folder_ids: set[UUID],
    ) -> UUID | None:
        """returns parent_id unchanged if it is being restored in this same
        batch or already exists outside the trash, otherwise falls back to
        root so the restored item is never left pointing at a trashed
        or missing parent"""
        if parent_id is None or parent_id in restored_folder_ids:
            return parent_id

        parent = await self._folders.get_by_id(parent_id, owner_id)
        if parent is None or parent.deleted_at is not None:
            return None

        return parent_id

    async def purge_batch(self, owner_id: UUID, trash_batch_id: UUID) -> None:
        folders = await self._folders.list_for_trash_batch(
            owner_id=owner_id, trash_batch_id=trash_batch_id
        )
        files = await self._files.list_for_trash_batch(
            owner_id=owner_id, trash_batch_id=trash_batch_id
        )

        if not folders and not files:
            raise TrashBatchNotFoundError

        for stored_file in files:
            await self._storage.delete(stored_file.storage_key)
            await self._files.delete(stored_file)

        for folder in folders:
            await self._folders.delete(folder)

        await self._session.commit()
