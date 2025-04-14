from fastapi import APIRouter

from src.presentation.api.middlewares.jwt_guard import current_user_dep

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_me(current_user: current_user_dep):
    return {"user": current_user.name}


@router.patch("/me")
async def update_me(current_user: current_user_dep):
    pass
