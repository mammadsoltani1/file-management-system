from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.search import SearchListing
from app.services.search_service import InvalidSearchQueryError, SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchListing)
async def search_filenames(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[str, Query(min_length=1, max_length=255)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> SearchListing:
    try:
        normalized_query, items, total_items = await SearchService(
            session
        ).search_filenames(
            owner_id=current_user.id, query=query, page=page, page_size=page_size
        )

    except InvalidSearchQueryError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="search query must contain at least one non whitespace character",
        ) from err

    total_pages = (total_items + page_size - 1) // page_size if total_items else 0

    return SearchListing(
        query=normalized_query,
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )
