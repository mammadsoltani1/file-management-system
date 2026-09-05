from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.files import router as files_router
from app.api.v1.folders import router as folders_router
from app.api.v1.search import router as search_router
from app.api.v1.shares import router as share_router
from app.api.v1.trash import router as trash_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(folders_router)
api_router.include_router(files_router)
api_router.include_router(trash_router)
api_router.include_router(search_router)
api_router.include_router(share_router)
