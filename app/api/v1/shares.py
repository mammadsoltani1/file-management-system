from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_file_service
from app.models.user import User
from app.schemas.file import FilePublic
from app.schemas.share import FileShareCreate, FileSharePublic, FileShareRecipientPublic
from app.services.file_service import (
    CannotShareFileWithOwnerError,
    FileAlreadySharedError,
    FileService,
    FileShareNotFoundError,
    ShareRecipientNotFoundError,
    StoredFileContentMissingError,
    StoredFileNotFoundError,
)

router = APIRouter(prefix="/shares", tags=["shares"])


def to_file_share_public(file_share) -> FileSharePublic:
    return FileSharePublic(
        id=file_share.id,
        file_id=file_share.file_id,
        owner_id=file_share.owner_id,
        recipient=FileShareRecipientPublic(
            id=file_share.recipient.id,
            email=file_share.recipient.email,
        ),
        created_at=file_share.created_at,
    )


@router.post(
    "/files/{file_id}",
    response_model=FileSharePublic,
    status_code=status.HTTP_201_CREATED,
)
async def share_file(
    file_id: UUID,
    payload: FileShareCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FileSharePublic:
    try:
        file_share = await file_service.share_file(
            owner_id=current_user.id,
            file_id=file_id,
            payload=payload,
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    except ShareRecipientNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no user exists with that email address",
        ) from err

    except CannotShareFileWithOwnerError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="a file cannot be shared with its owner",
        ) from err

    except FileAlreadySharedError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="the file is already shared with this user",
        ) from err

    return to_file_share_public(file_share)


@router.get(
    "/files/{file_id}",
    response_model=list[FileSharePublic],
)
async def list_file_shares(
    file_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> list[FileSharePublic]:
    try:
        shares = await file_service.list_file_shares(
            owner_id=current_user.id,
            file_id=file_id,
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    return [to_file_share_public(file_share) for file_share in shares]


@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_file_share(
    share_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> None:
    try:
        await file_service.revoke_file_share(
            owner_id=current_user.id,
            share_id=share_id,
        )

    except FileShareNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested share was not found",
        ) from err


@router.get("/received/files", response_model=list[FilePublic])
async def list_received_files(
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> list[FilePublic]:
    files = await file_service.list_received_files(recipient_id=current_user.id)
    return [FilePublic.model_validate(file) for file in files]


@router.get("/received/files/{file_id}/download")
async def download_shared_file(
    file_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    try:
        stored_file, path = await file_service.get_shared_download_file(
            recipient_id=current_user.id,
            file_id=file_id,
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the shared file was not found",
        ) from err

    except StoredFileContentMissingError as err:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="the shared file content is unavailable",
        ) from err

    return FileResponse(
        path=path,
        media_type=stored_file.content_type,
        filename=stored_file.name,
    )
