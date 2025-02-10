from contextlib import asynccontextmanager
from sys import prefix

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone

from src.core.config import settings
from src.infrastructure.database.session import engine
from src.infrastructure.cache.redis.connection import init_redis_pool, close_redis_pool
from src.presentation.api import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Инициализируем подключения к БД и Redis
    app.state.redis = await init_redis_pool()

    yield

    # Shutdown
    # Закрываем подключения
    await close_redis_pool(app.state.redis)
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan, prefix="api/v1")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене нужно указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Здесь будем подключать роутеры
app.include_router(auth_router)
# app.include_router(messages_router)
# и т.д.


@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc),
        "redis": await app.state.redis.ping(),  # Проверяем подключение к Redis
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
