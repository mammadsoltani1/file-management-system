from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stored_file import StoredFile


class FileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, stored_file: StoredFile) -> None:
        self._session.add(stored_file)