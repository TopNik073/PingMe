from typing import Annotated, TYPE_CHECKING

from fastapi import APIRouter, Depends

from src.presentation.api.middlewares.jwt_guard import get_current_user

if TYPE_CHECKING:
    from src.infrastructure.database.models.users import Users

router = APIRouter(prefix="/conversation", tags=["Conversations"])


@router.post("/")
async def create_conversation(current_user: Annotated["Users", Depends(get_current_user)]):
    pass


@router.patch("/")
async def create_conversation(current_user: Annotated["Users", Depends(get_current_user)]):
    pass


@router.post("/join")
async def join_to_conversation(current_user: Annotated["Users", Depends(get_current_user)]):
    pass


@router.get("/messages")
async def get_messages(current_user: Annotated["Users", Depends(get_current_user)]):
    pass


@router.get("/participants")
async def get_participants(current_user: Annotated["Users", Depends(get_current_user)]):
    pass


@router.get("/media")
async def get_media(current_user: Annotated["Users", Depends(get_current_user)]):
    pass
