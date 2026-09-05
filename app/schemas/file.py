from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class BulkFileOperation(BaseModel):
    file_ids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator("file_ids")
    @classmethod
    def file_ids_must_be_unique(cls, file_ids: list[UUID]) -> list[UUID]:
        if len(file_ids) != len(set(file_ids)):
            raise ValueError("file ids must not contain duplicates")
        return file_ids


class BulkFileMove(BulkFileOperation):
    # uuid to move into a specific folder or None to move to root
    folder_id: UUID | None


class BulkFileCopy(BulkFileOperation):
    # uuid to copy into a specific folder or None to copy to root
    folder_id: UUID | None
