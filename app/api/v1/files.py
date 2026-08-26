from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_current_user, get_file_service
from app.models.user import User
from app.schemas.file import FilePublic
from app.services.file_service import (
    FileService,
    FileTooLargeError,
    InvalidFilenameError,
    UploadFolderNotFoundError,
)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FilePublic, status_code=status.HTTP_201_CREATED)
async def upload_file(
    upload: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
    folder_id: Annotated[UUID | None, Form()] = None,
) -> FilePublic:
    try:
        return await file_service.upload_file(
            owner_id=current_user.id, upload=upload, folder_id=folder_id
        )

    except UploadFolderNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload folder was not found"
        ) from err

    except InvalidFilenameError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="the uploaded filename is invalid",
        ) from err

    except FileTooLargeError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="the uploaded file exceeds the configured size limit",
        ) from err
