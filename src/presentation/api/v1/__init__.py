from fastapi import APIRouter
from src.presentation.api.v1.auth.router import router as auth_router
from src.presentation.api.v1.users.router import router as user_router
from src.presentation.api.v1.conversations.router import router as conversation_router

V1_ROUTER = APIRouter(prefix="/api/v1")

V1_ROUTER.include_router(auth_router)
V1_ROUTER.include_router(user_router)
V1_ROUTER.include_router(conversation_router)
