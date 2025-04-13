from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from src.presentation.api.middlewares.jwt_guard import get_current_user

if TYPE_CHECKING:
    from src.infrastructure.database.models.users import Users

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_me(current_user: Annotated["Users", Depends(get_current_user)]):
    return {"user": current_user.name}


@router.patch("/me")
async def update_me(current_user: Annotated["Users", Depends(get_current_user)]):
    pass
