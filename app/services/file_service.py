import hashlib
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.stored_file import StoredFile
from app.repositories.file_repository import FileRepo
from app.repositories.folder_repository import FolderRepo
from app.storage.base import StorageProvider


class FileTooLargeError(Exception):
    """raised when an upload exceeds the configured size limit"""


class UploadFolderNotFoundError(Exception):
    """raised when an upload target folder is unavailable to the user"""


class InvalidFilenameError(Exception):
    """raised when an uploaded filename is unavailable or unsafe"""


class FileService:
    def __init__(self, session: AsyncSession, storage: StorageProvider) -> None:
        self._session = session
        self._storage = storage
        self._files = FileRepo(session)
        self._folders = FolderRepo(session)

    async def upload_file(
        self, *, owner_id: UUID, folder_id: UUID | None, upload: UploadFile
    ) -> StoredFile:
        original_filename = self._sanitize_filename(upload.filename)

        if folder_id is not None:
            folder = await self._folders.get_for_owner(folder_id, owner_id)

            if folder is None:
                raise UploadFolderNotFoundError
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
                original_filename=original_filename,
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
