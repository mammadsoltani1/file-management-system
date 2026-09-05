import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.file_share import FileShare
from app.models.folder import Folder
from app.models.stored_file import StoredFile
from app.models.user import User
from app.repositories.file_repository import FileRepo
from app.repositories.file_share_repository import FileShareRepo
from app.repositories.folder_repository import FolderRepo
from app.schemas.file import BulkFileCopy, BulkFileMove, FileCopy, FileMove, FileRename
from app.schemas.share import FileShareCreate
from app.storage.base import StorageProvider


class FileTooLargeError(Exception):
    """raised when an upload exceeds the configured size limit"""


class UploadFolderNotFoundError(Exception):
    """raised when an upload target folder is unavailable to the user"""


class InvalidFilenameError(Exception):
    """raised when an uploaded filename is unavailable or unsafe"""


class StoredFileNotFoundError(Exception):
    """raised when a file does not exist or is not owned by the user"""


class StoredFileContentMissingError(Exception):
    """raised when the files metadata exists but its physical content is missing"""


class DestinationFolderNotFoundError(Exception):
    """raised when a file move target folder is unavailable to the user"""


class FilenameAlreadyExistsError(Exception):
    """raised when a file with the same name already exists in the target folder"""


class CopyDestinationFolderNotFound(Exception):
    """raised when a file copy target folder is unavailable to the user"""


class BulkFileNotFoundError(Exception):
    """raised when one or more selected files do not belong to the user"""


class BulkFilenameConflictError(Exception):
    """raised when a bulk operation would create duplicate filenames"""


class ShareRecipientNotFoundError(Exception):
    """raised when the requested recipient email has no user"""


class CannotShareFileWithOwnerError(Exception):
    """raised when the owner tries to share a file with themselves"""


class FileAlreadySharedError(Exception):
    """raised when a file is already shared with the target user"""


class FileShareNotFoundError(Exception):
    """raised when a share record can't be found for the file owner"""


class FileService:
    def __init__(self, session: AsyncSession, storage: StorageProvider) -> None:
        self._session = session
        self._storage = storage
        self._files = FileRepo(session)
        self._folders = FolderRepo(session)
        self._shares = FileShareRepo(session)

    async def upload_file(
        self, owner_id: UUID, folder_id: UUID | None, upload: UploadFile
    ) -> StoredFile:
        name = self._sanitize_filename(upload.filename)

        if folder_id is not None:
            folder = await self._folders.get_for_owner(folder_id, owner_id)

            if folder is None:
                raise UploadFolderNotFoundError

        if await self._files.exists_with_name(owner_id, folder_id, name):
            raise FilenameAlreadyExistsError

        file_id = uuid4()
        storage_key = f"users/{owner_id}/files/{file_id}"
        content_hash = hashlib.sha256()

        async def file_chunks() -> AsyncIterator[bytes]:
            uploaded_size = 0

            while chunk := await upload.read(1024 * 1024):
                uploaded_size += len(chunk)
                if uploaded_size > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise FileTooLargeError

                content_hash.update(chunk)
                yield chunk

        file_was_written = False
        try:
            size_bytes = await self._storage.save(
                key=storage_key, content=file_chunks()
            )
            file_was_written = True
            stored_file = StoredFile(
                id=file_id,
                owner_id=owner_id,
                folder_id=folder_id,
                name=name,
                storage_key=storage_key,
                content_type=upload.content_type,
                size_bytes=size_bytes,
                sha256=content_hash.hexdigest(),
            )
            self._files.add(stored_file)
            await self._session.commit()
            await self._session.refresh(stored_file)
            return stored_file

        except Exception:
            await self._session.rollback()
            if file_was_written:
                await self._storage.delete(storage_key)
            raise

        finally:
            await upload.close()

    @staticmethod
    def _sanitize_filename(filename: str | None) -> str:
        if filename is None:
            raise InvalidFilenameError

        normalized = filename.replace("\\", "/")
        safe_filename = Path(normalized).name.strip()

        if (
            not safe_filename
            or safe_filename in {".", ".."}
            or len(safe_filename) > 255
        ):
            raise InvalidFilenameError

        return safe_filename

    async def list_directory(
        self, *, owner_id: UUID, folder_id: UUID | None, page: int, page_size: int
    ) -> tuple[list[Folder], list[StoredFile], int]:
        # a null folder id means the user's root page
        if folder_id is not None:
            folder = await self._folders.get_for_owner(folder_id, owner_id)
            if folder is None:
                raise UploadFolderNotFoundError

        folder_cnt = await self._folders.count_for_parent(
            owner_id=owner_id, parent_id=folder_id
        )
        file_cnt = await self._files.count_for_folder(
            owner_id=owner_id, folder_id=folder_id
        )

        total_items = folder_cnt + file_cnt
        offset = (page - 1) * page_size

        # directory ordering: folders first, then files, both sorted by name ascending
        if offset < folder_cnt:
            folders = await self._folders.list_for_parent_page(
                owner_id=owner_id, parent_id=folder_id, offset=offset, limit=page_size
            )
            remaining_limit = page_size - len(folders)
            if remaining_limit > 0:
                files = await self._files.list_for_folder_page(
                    folder_id=folder_id,
                    owner_id=owner_id,
                    offset=0,
                    limit=remaining_limit,
                )
            else:
                files = []

        else:
            folders = []
            file_offset = offset - folder_cnt
            files = await self._files.list_for_folder_page(
                folder_id=folder_id,
                owner_id=owner_id,
                offset=file_offset,
                limit=page_size,
            )

        return folders, files, total_items

    async def get_download_file(
        self, owner_id: UUID, file_id: UUID
    ) -> tuple[StoredFile, Path]:
        stored_file = await self._files.get_for_owner(
            file_id=file_id, owner_id=owner_id
        )

        if stored_file is None:
            raise StoredFileNotFoundError
        if not await self._storage.exists(stored_file.storage_key):
            raise StoredFileContentMissingError

        path = await self._storage.get_path(stored_file.storage_key)
        return stored_file, path

    async def delete_file(self, owner_id: UUID, file_id: UUID) -> None:
        stored_file = await self._files.get_for_owner(
            file_id=file_id, owner_id=owner_id
        )

        if stored_file is None:
            raise StoredFileNotFoundError

        stored_file.deleted_at = datetime.now(UTC)
        stored_file.trash_batch_id = uuid4()

        await self._session.commit()
        await self._session.refresh(stored_file)

    async def rename_file(
        self, owner_id: UUID, file_id: UUID, payload: FileRename
    ) -> StoredFile:
        stored_file = await self._files.get_for_owner(
            file_id=file_id, owner_id=owner_id
        )

        if stored_file is None:
            raise StoredFileNotFoundError

        name = self._sanitize_filename(payload.name)

        # check if a file with the new name already exists in the same folder
        if await self._files.exists_with_name(
            owner_id, stored_file.folder_id, name, exclude_file_id=file_id
        ):
            raise FilenameAlreadyExistsError

        stored_file.name = name
        await self._session.commit()
        await self._session.refresh(stored_file)
        return stored_file

    async def move_file(
        self, owner_id: UUID, file_id: UUID, payload: FileMove
    ) -> StoredFile:
        stored_file = await self._files.get_for_owner(
            file_id=file_id, owner_id=owner_id
        )

        if stored_file is None:
            raise StoredFileNotFoundError

        destination_folder_id = payload.folder_id
        if destination_folder_id is not None:
            destination_folder = await self._folders.get_for_owner(
                folder_id=destination_folder_id, owner_id=owner_id
            )
            if destination_folder is None:
                raise DestinationFolderNotFoundError

        duplicate_exists = await self._files.exists_with_name(
            owner_id=owner_id,
            folder_id=destination_folder_id,
            name=stored_file.name,
            exclude_file_id=file_id,
        )

        if duplicate_exists:
            raise FilenameAlreadyExistsError

        stored_file.folder_id = destination_folder_id
        await self._session.commit()
        await self._session.refresh(stored_file)
        return stored_file

    async def copy_file(
        self, owner_id: UUID, file_id: UUID, payload: FileCopy
    ) -> StoredFile:
        source_file = await self._files.get_for_owner(
            file_id=file_id, owner_id=owner_id
        )
        if source_file is None:
            raise StoredFileNotFoundError

        destination_folder_id = payload.folder_id

        if destination_folder_id is not None:
            destination_folder = await self._folders.get_for_owner(
                folder_id=destination_folder_id, owner_id=owner_id
            )

            if destination_folder is None:
                raise CopyDestinationFolderNotFound

        duplicate_exists = await self._files.exists_with_name(
            owner_id=owner_id, folder_id=destination_folder_id, name=source_file.name
        )

        if duplicate_exists:
            raise FilenameAlreadyExistsError
        if not await self._storage.exists(source_file.storage_key):
            raise StoredFileContentMissingError

        copied_file_id = uuid4()
        copied_storage_key = f"users/{owner_id}/files/{copied_file_id}"

        content_was_copied = False

        try:
            await self._storage.copy(
                source_key=source_file.storage_key, destination_key=copied_storage_key
            )
            content_was_copied = True

            copied_file = StoredFile(
                id=copied_file_id,
                owner_id=owner_id,
                folder_id=destination_folder_id,
                name=source_file.name,
                storage_key=copied_storage_key,
                content_type=source_file.content_type,
                size_bytes=source_file.size_bytes,
                sha256=source_file.sha256,
            )

            self._files.add(copied_file)
            await self._session.commit()
            await self._session.refresh(copied_file)

            return copied_file
        except Exception:
            await self._session.rollback()
            if content_was_copied:
                await self._storage.delete(copied_storage_key)
            raise

    async def _get_active_files_for_bulk_operation(
        self, owner_id: UUID, file_ids: list[UUID]
    ) -> list[StoredFile]:
        files = await self._files.list_active_for_owner_by_ids(
            owner_id=owner_id, file_ids=file_ids
        )

        if len(files) != len(file_ids):
            raise BulkFileNotFoundError
        return files

    async def _validate_bulk_destination(
        self, owner_id: UUID, destination_folder_id: UUID | None
    ) -> None:
        if destination_folder_id is None:
            return
        destination_folder = await self._folders.get_for_owner(
            folder_id=destination_folder_id, owner_id=owner_id
        )
        if destination_folder is None:
            raise DestinationFolderNotFoundError

    async def _validate_bulk_name_conflicts(
        self,
        owner_id: UUID,
        files: list[StoredFile],
        destination_folder_id: UUID | None,
        exclude_selected_files: bool,
    ) -> None:
        """ensures every destination filename is unique
        for move selected files are excluded from the destination check because they are leaving their current location all together
        for copy selected files remain in their original location and because of that they must not be excluded
        """
        names = [file.name for file in files]
        if len(names) != len(set(names)):
            raise BulkFilenameConflictError

        destination_files = await self._files.list_for_owner(
            owner_id=owner_id, folder_id=destination_folder_id
        )

        file_ids = [file.id for file in files]

        for file in destination_files:
            if exclude_selected_files and file.id in file_ids:
                continue
            if file.name in names:
                raise BulkFilenameConflictError

    async def bulk_delete_files(self, owner_id: UUID, file_ids: list[UUID]) -> None:
        files = await self._get_active_files_for_bulk_operation(
            owner_id=owner_id, file_ids=file_ids
        )

        trash_batch_id = uuid4()
        deleted_at = datetime.now(UTC)

        try:
            for file in files:
                file.deleted_at = deleted_at
                file.trash_batch_id = trash_batch_id

            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def bulk_move_files(self, owner_id: UUID, payload: BulkFileMove) -> None:
        files = await self._get_active_files_for_bulk_operation(
            owner_id=owner_id, file_ids=payload.file_ids
        )

        await self._validate_bulk_destination(
            owner_id=owner_id, destination_folder_id=payload.folder_id
        )

        await self._validate_bulk_name_conflicts(
            owner_id=owner_id,
            files=files,
            destination_folder_id=payload.folder_id,
            exclude_selected_files=True,
        )

        try:
            for file in files:
                file.folder_id = payload.folder_id
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def bulk_copy_files(
        self, owner_id: UUID, payload: BulkFileCopy
    ) -> list[StoredFile]:
        files = await self._get_active_files_for_bulk_operation(
            owner_id=owner_id, file_ids=payload.file_ids
        )

        await self._validate_bulk_destination(
            owner_id=owner_id, destination_folder_id=payload.folder_id
        )

        await self._validate_bulk_name_conflicts(
            owner_id=owner_id,
            files=files,
            destination_folder_id=payload.folder_id,
            exclude_selected_files=False,
        )

        missing_content = [
            file for file in files if not await self._storage.exists(file.storage_key)
        ]

        if missing_content:
            raise StoredFileContentMissingError

        copied_files: list[StoredFile] = []
        copied_storage_keys: list[str] = []

        try:
            for source_file in files:
                copied_file_id = uuid4()
                copied_storage_key = f"users/{owner_id}/files/{copied_file_id}"

                await self._storage.copy(
                    source_key=source_file.storage_key,
                    destination_key=copied_storage_key,
                )

                copied_storage_keys.append(copied_storage_key)
                copied_file = StoredFile(
                    id=copied_file_id,
                    owner_id=owner_id,
                    folder_id=payload.folder_id,
                    name=source_file.name,
                    storage_key=copied_storage_key,
                    content_type=source_file.content_type,
                    size_bytes=source_file.size_bytes,
                    sha256=source_file.sha256,
                )

                self._files.add(copied_file)
                copied_files.append(copied_file)
            await self._session.commit()

            for copied_file in copied_files:
                await self._session.refresh(copied_file)

            return copied_files
        except Exception:
            await self._session.rollback()

            for storage_key in copied_storage_keys:
                await self._storage.delete(storage_key)
            raise

    async def share_file(
        self, owner_id: UUID, file_id: UUID, payload: FileShareCreate
    ) -> FileShare:
        file = await self._files.get_for_owner(file_id=file_id, owner_id=owner_id)

        if file is None:
            raise StoredFileNotFoundError

        statement = select(User).where(User.email == payload.recipient_email)
        result = await self._session.scalars(statement)
        recipient = result.one_or_none()

        if recipient is None:
            raise ShareRecipientNotFoundError
        if recipient.id == owner_id:
            raise CannotShareFileWithOwnerError

        existing_share = await self._shares.get_for_file_and_recipient(
            file_id=file_id, recipient_id=recipient.id
        )
        if existing_share is not None:
            raise FileAlreadySharedError

        file_share = FileShare(
            file_id=file.id, owner_id=owner_id, recipient_id=recipient.id
        )
        self._shares.add(file_share)

        try:
            await self._session.commit()
            await self._session.refresh(file_share, attribute_names=["recipient"])
        except Exception:
            await self._session.rollback()
            raise

        return file_share

    async def list_file_shares(self, owner_id: UUID, file_id: UUID) -> list[FileShare]:
        file = await self._files.get_for_owner(owner_id=owner_id, file_id=file_id)

        if file is None:
            raise StoredFileNotFoundError

        return await self._shares.list_for_file_owner(
            file_id=file_id, owner_id=owner_id
        )

    async def revoke_file_share(self, owner_id: UUID, share_id: UUID) -> None:
        file_share = await self._shares.get_for_owner(
            share_id=share_id, owner_id=owner_id
        )
        if file_share is None:
            raise FileShareNotFoundError
        try:
            await self._shares.delete(file_share)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def list_received_files(self, recipient_id: UUID) -> list[StoredFile]:
        shares = await self._shares.list_received_by_user(recipient_id=recipient_id)
        return [share.file for share in shares if share.file.deleted_at is None]

    async def get_shared_download_file(
        self, recipient_id: UUID, file_id: UUID
    ) -> tuple[StoredFile, Path]:
        file_share = await self._shares.get_for_file_and_recipient(
            file_id=file_id, recipient_id=recipient_id
        )
        if file_share is None:
            raise StoredFileNotFoundError
        file = await self._files.get_for_owner(
            file_id=file_id, owner_id=file_share.owner_id
        )

        if file is None:
            raise StoredFileNotFoundError

        if not await self._storage.exists(file.storage_key):
            raise StoredFileContentMissingError

        path = await self._storage.get_path(file.storage_key)

        return file, path
