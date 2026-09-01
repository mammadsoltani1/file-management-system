from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user, get_trash_service
from app.models.user import User
from app.schemas.trash import TrashListing
from app.services.file_service import FilenameAlreadyExistsError
from app.services.folder_service import FolderAlreadyExistsError
from app.services.trash_service import TrashBatchNotFoundError, TrashService

router = APIRouter(prefix="/trash", tags=["trash"])


@router.get("", response_model=TrashListing)
async def list_trash(
    current_user: Annotated[User, Depends(get_current_user)],
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> TrashListing:
    folders, files = await trash_service.list_trash(owner_id=current_user.id)
    return TrashListing(folders=folders, files=files)


@router.post("/{trash_batch_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_trash_batch(
    trash_batch_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> Response:
    try:
        await trash_service.restore_batch(
            owner_id=current_user.id, trash_batch_id=trash_batch_id
        )

    except TrashBatchNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no trashed items were found for this batch",
        ) from err

    except (FolderAlreadyExistsError, FilenameAlreadyExistsError) as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="restoring this item would collide with an existing name",
        ) from err

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{trash_batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_trash_batch(
    trash_batch_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> Response:
    try:
        await trash_service.purge_batch(
            owner_id=current_user.id, trash_batch_id=trash_batch_id
        )

    except TrashBatchNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no trashed items were found for this batch",
        ) from err

    return Response(status_code=status.HTTP_204_NO_CONTENT)
