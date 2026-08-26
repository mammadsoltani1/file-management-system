from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.models.user import User
from app.services.file_service import FileService
from app.services.folder_service import FolderService
from app.storage.base import StorageProvider
from app.storage.dependencies import get_storage_provider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        subject = payload.get("sub")
        user_id = UUID(subject)
    except (InvalidTokenError, TypeError, ValueError) as err:
        raise credential_exception from err

    user = await session.get(User, user_id)
    if user is None:
        raise credential_exception

    return user


def get_folder_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FolderService:
    return FolderService(session)


def get_file_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> FileService:
    return FileService(session=session, storage=storage)
