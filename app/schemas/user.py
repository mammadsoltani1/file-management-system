from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    created_at: datetime