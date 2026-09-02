from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: UUID
    item_type: Literal["file", "folder"]
    name: str
    parent_id: UUID | None
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime
    updated_at: datetime


class SearchListing(BaseModel):
    query: str
    items: list[SearchResult]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
