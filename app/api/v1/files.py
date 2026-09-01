from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_file_service
from app.models.user import User
from app.schemas.directory import DirectoryListing
from app.schemas.file import FilePublic
from app.services.file_service import (
    DestinationFolderNotFoundError,
    FileMove,
    FilenameAlreadyExistsError,
    FileRename,
    FileService,
    FileTooLargeError,
    InvalidFilenameError,
    StoredFileContentMissingError,
    StoredFileNotFoundError,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="the uploaded filename is invalid",
        ) from err

    except FilenameAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a file with the same name already exists in this folder",
        ) from err

    except FileTooLargeError as err:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="the uploaded file exceeds the configured size limit",
        ) from err


@router.get("", response_model=DirectoryListing)
async def list_directory(
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
    folder_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DirectoryListing:
    try:
        folders, files, total_items = await file_service.list_directory(
            owner_id=current_user.id,
            folder_id=folder_id,
            page=page,
            page_size=page_size,
        )

    except UploadFolderNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested folder was not found",
        ) from err

    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    return DirectoryListing(
        folder_id=folder_id,
        folders=folders,
        files=files,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    try:
        stored_file, path = await file_service.get_download_file(
            owner_id=current_user.id, file_id=file_id
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    except StoredFileContentMissingError as err:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="the file record exists, but its stored content is unavailable",
        ) from err

    return FileResponse(
        path=path,
        media_type=stored_file.content_type,
        filename=stored_file.name,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    try:
        await file_service.delete_file(owner_id=current_user.id, file_id=file_id)

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{file_id}/rename", response_model=FilePublic)
async def rename_file(
    file_id: UUID,
    payload: FileRename,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FilePublic:
    try:
        return await file_service.rename_file(
            owner_id=current_user.id, file_id=file_id, payload=payload
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    except InvalidFilenameError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="the uploaded filename is invalid",
        ) from err

    except FilenameAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a file with the same name already exists in this target folder",
        ) from err


@router.patch("/{file_id}/move", response_model=FilePublic)
async def move_file(
    file_id: UUID,
    payload: FileMove,
    current_user: Annotated[User, Depends(get_current_user)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FilePublic:
    try:
        return await file_service.move_file(
            owner_id=current_user.id, file_id=file_id, payload=payload
        )

    except StoredFileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the requested file was not found",
        ) from err

    except DestinationFolderNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="the destination folder was not found",
        ) from err

    except FilenameAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a file with the same name already exists in this target folder",
        ) from err
