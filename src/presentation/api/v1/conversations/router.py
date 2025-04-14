from fastapi import APIRouter, Depends

from src.presentation.api.middlewares.jwt_guard import current_user_dep


router = APIRouter(prefix="/conversation", tags=["Conversations"])


@router.post("/")
async def create_conversation(current_user: current_user_dep):
    pass


@router.patch("/")
async def update_conversation(current_user: current_user_dep):
    pass


@router.post("/join")
async def join_to_conversation(current_user: current_user_dep):
    pass


@router.get("/messages")
async def get_messages(current_user: current_user_dep):
    pass


@router.get("/participants")
async def get_participants(current_user: current_user_dep):
    pass


@router.get("/media")
async def get_media(current_user: current_user_dep):
    pass
