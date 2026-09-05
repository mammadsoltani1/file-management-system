from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class FileShareCreate(BaseModel):
    recipient_email: EmailStr


class FileShareRecipientPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr


class FileSharePublic(BaseModel):
    id: UUID
    file_id: UUID
    owner_id: UUID
    recipient: FileShareRecipientPublic
    created_at: datetime
