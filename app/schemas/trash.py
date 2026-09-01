from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrashedFolder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    deleted_at: datetime
    trash_batch_id: UUID


class TrashedFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    folder_id: UUID | None
    deleted_at: datetime
    trash_batch_id: UUID


class TrashListing(BaseModel):
    folders: list[TrashedFolder]
    files: list[TrashedFile]
