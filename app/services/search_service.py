from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.file_repository import FileRepo
from app.repositories.folder_repository import FolderRepo
from app.schemas.search import SearchResult


class InvalidSearchQueryError(Exception):
    """raised when the query has no searchable content"""


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._files = FileRepo(session)
        self._folders = FolderRepo(session)

    async def search_filenames(
        self, owner_id: UUID, query: str, page: int, page_size: int
    ) -> tuple[str, list[SearchResult], int]:
        normalized_query = query.strip()

        if not normalized_query:
            raise InvalidSearchQueryError

        folders = await self._folders.search_for_owner(
            owner_id=owner_id, query=normalized_query
        )
        files = await self._files.search_for_owner(
            owner_id=owner_id, query=normalized_query
        )

        results = [
            SearchResult(
                id=folder.id,
                item_type="folder",
                name=folder.name,
                parent_id=folder.parent_id,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
            )
            for folder in folders
        ]

        results.extend(
            SearchResult(
                id=file.id,
                item_type="file",
                name=file.name,
                parent_id=file.folder_id,
                created_at=file.created_at,
                updated_at=file.updated_at,
                content_type=file.content_type,
                size_bytes=file.size_bytes,
            )
            for file in files
        )

        results.sort(
            key=lambda result: (
                result.name.casefold(),
                result.item_type,
                str(result.id),
            )
        )

        total_items = len(results)
        offset = (page - 1) * page_size

        return (normalized_query, results[offset : offset + page_size], total_items)
