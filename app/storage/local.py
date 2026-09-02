from collections.abc import AsyncIterator
from pathlib import Path

import anyio

from app.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """store files on the local server file system"""

    def __init__(self, root_directory: Path) -> None:
        self._root_directory = root_directory.resolve()

    def _resolve_key(self, key: str) -> Path:
        relative_path = Path(key)

        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("invalid storage key")

        full_path = (self._root_directory / relative_path).resolve()

        if not full_path.is_relative_to(self._root_directory):
            raise ValueError("invalid storage key")

        return full_path

    async def save(self, *, key: str, content: AsyncIterator[bytes]) -> int:
        destination = self._resolve_key(key)

        await anyio.to_thread.run_sync(
            lambda: destination.parent.mkdir(parents=True, exist_ok=True)
        )

        bytes_written = 0
        try:
            async with await anyio.open_file(destination, "wb") as file:
                async for chunk in content:
                    bytes_written += len(chunk)
                    await file.write(chunk)
        except Exception:
            await self.delete(key)
            raise

        return bytes_written

    async def get_path(self, key: str) -> Path:
        return self._resolve_key(key)

    async def delete(self, key: str) -> None:
        path = self._resolve_key(key)

        if await anyio.to_thread.run_sync(path.exists):
            await anyio.to_thread.run_sync(path.unlink)

    async def exists(self, key: str) -> bool:
        path = self._resolve_key(key)
        return await anyio.to_thread.run_sync(path.is_file)

    async def copy(self, source_key: str, destination_key: str) -> None:
        source = self._resolve_key(source_key)
        destination = self._resolve_key(destination_key)

        if not await anyio.to_thread.run_sync(source.is_file):
            raise FileNotFoundError(source_key)

        await anyio.to_thread.run_sync(
            lambda: destination.parent.mkdir(parents=True, exist_ok=True)
        )

        try:
            await anyio.to_thread.run_sync(
                lambda: destination.write_bytes(source.read_bytes())
            )

        except Exception:
            await self.delete(destination_key)
            raise
