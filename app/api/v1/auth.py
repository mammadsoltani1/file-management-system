from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_passwords, verify_password
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import Token, UserRegister
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService, RefreshTokenInvalidError

router = APIRouter(prefix="/auth", tags=["authentication"])


def _client_ip(req: Request) -> str | None:
    if req.client is None:
        return None
    return req.client.host


def _set_refresh_cookie(res: Response, token: str) -> None:
    res.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
    )


def _clear_refresh_cookie(res: Response) -> None:
    res.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
    )


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
async def register_user(
    payload: UserRegister, session: AsyncSession = Depends(get_db_session)
) -> User:
    user = User(
        email=payload.email.lower(), password_hash=hash_passwords(payload.password)
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an account with this email already exists",
        ) from err

    await session.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login_user(
    req: Request,
    res: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> Token:
    result = await session.execute(
        Select(User).where(User.email == form_data.username.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    refresh_token = await AuthService(session).create_refresh_session(
        user_id=user.id,
        ip_address=_client_ip(req),
        user_agent=req.headers.get("user-agent"),
    )

    _set_refresh_cookie(res, refresh_token)

    return Token(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=Token)
async def refresh_token(
    req: Request, res: Response, session: AsyncSession = Depends(get_db_session)
) -> Token:
    refresh_token = req.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token is missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id, successor_token = await AuthService(session).rotate_refresh_session(
            raw_token=refresh_token,
            ip_address=_client_ip(req),
            user_agent=req.headers.get("user-agent"),
        )
    except RefreshTokenInvalidError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token is invalid or expired or missing",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    _set_refresh_cookie(res, successor_token)

    return Token(access_token=create_access_token(str(user_id)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    req: Request, session: AsyncSession = Depends(get_db_session)
) -> Response:
    token = req.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    if token is not None:
        await AuthService(session).revoke_refresh_session(raw_token=token)

    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(res)
    return res


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_devices(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await AuthService(session).revoke_all_for_user(user_id=current_user.id)

    res = Response(status_code=status.HTTP_204_NO_CONTENT)

    _clear_refresh_cookie(res)

    return res
