from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None


class FolderRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderMove(BaseModel):
    # UUID moves into a folder, None moves to root
    parent_id: UUID | None = None


class FolderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    parent_id: UUID | None
    name: str
    created_at: datetime
    updated_at: datetime
