from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    folder_id: UUID | None
    name: str
    content_type: str | None
    size_bytes: int
    sha256: str | None
    created_at: datetime
    updated_at: datetime


class FileRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FileMove(BaseModel):
    # uuid to move into a specific folder or None to move to root
    folder_id: UUID | None


class FileCopy(BaseModel):
    # uuid to copy into a specific folder or None to copy to root
    folder_id: UUID | None
