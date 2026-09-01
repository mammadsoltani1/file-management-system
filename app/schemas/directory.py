from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.file import FilePublic
from app.schemas.folder import FolderPublic


class DirectoryListing(BaseModel):
    folder_id: UUID | None
    folders: list[FolderPublic]
    files: list[FilePublic]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
