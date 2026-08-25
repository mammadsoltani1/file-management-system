from fastapi import APIRouter
from app.api.v1.auth import router

api_router = APIRouter()
api_router.include_router(router)