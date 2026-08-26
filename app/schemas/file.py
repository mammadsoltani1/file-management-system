from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    folder_id: UUID | None
    original_filename: str
    content_type: str | None
    size_bytes: int
    sha256: str | None
    created_at: datetime
    updated_at: datetime
