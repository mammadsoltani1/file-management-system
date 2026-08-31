from uuid import UUID

from pydantic import BaseModel

from app.schemas.file import FilePublic
from app.schemas.folder import FolderPublic


class DirectoryListing(BaseModel):
    folder_id: UUID | None
    folders: list[FolderPublic]
    files: list[FilePublic]
