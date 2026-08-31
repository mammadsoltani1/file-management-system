from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user, get_folder_service
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderPublic
from app.services.folder_service import (
    FolderAlreadyExistsError,
    FolderNotEmptyError,
    FolderNotFoundError,
    FolderService,
    ParentFolderNotFoundError,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", response_model=FolderPublic, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    folder_service: Annotated[FolderService, Depends(get_folder_service)],
) -> FolderPublic:
    try:
        return await folder_service.create_folder(
            owner_id=current_user.id, payload=payload
        )

    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err)
        ) from err

    except ParentFolderNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="parent folder was not found"
        ) from err

    except FolderAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a folder with this name already exists here",
        ) from err


@router.get("", response_model=list[FolderPublic])
async def list_folders(
    current_user: Annotated[User, Depends(get_current_user)],
    folder_service: Annotated[FolderService, Depends(get_folder_service)],
    parent_id: UUID | None = Query(default=None),
) -> list[FolderPublic]:
    return await folder_service.list_folders(
        owner_id=current_user.id, parent_id=parent_id
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    folder_service: Annotated[FolderService, Depends(get_folder_service)],
    recursive: bool = Query(default=False),
) -> Response:
    try:
        await folder_service.delete_folder(
            owner_id=current_user.id, folder_id=folder_id, recursive=recursive
        )

    except FolderNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested folder was not found",
        ) from err

    except FolderNotEmptyError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="folder is not empty, retry with recursive=True to delete its content",
        ) from err

    return Response(status_code=status.HTTP_204_NO_CONTENT)
