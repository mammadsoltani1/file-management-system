from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol


class StorageProvider(Protocol):
    """contract for a phsyical file storage backend"""

    async def save(self, *, key: str, content: AsyncIterator[bytes]) -> int:
        """storage content under a key and return bytes written"""

    async def get_path(self, key: str) -> Path:
        """return the on disk path for a stored file"""

    async def delete(self, key: str) -> None:
        """delete a stored file if exists"""

    async def exists(self, key: str) -> bool:
        """return wether a stored file exists"""
