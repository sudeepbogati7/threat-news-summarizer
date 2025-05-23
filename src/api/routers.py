from fastapi import APIRouter
from .endpoints import auth, news

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(news.router, prefix="/news", tags=["News"])
