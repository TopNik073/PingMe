from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone

from src.core.config import settings
from src.core.logging import get_logger
from src.infrastructure.database.session import engine
from src.infrastructure.cache.redis.connection import init_redis_pool, close_redis_pool

# ROUTERS
from src.presentation.api.system.router import router as system_router
from src.presentation.api.v1 import V1_ROUTER

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing application dependencies")

    # Initialize connections to the database and Redis
    app.state.redis = await init_redis_pool()
    app.state.start_time = datetime.now(timezone.utc)

    docs_route = f"http://{settings.APP_HOST}:{settings.APP_PORT}/docs"
    logger.info(f"Application started successfully. See docs here {docs_route}")
    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close connections
    await close_redis_pool(app.state.redis)
    await engine.dispose()

    logger.info("Application shutdown complete")


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect routers
app.include_router(V1_ROUTER)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False, log_level=40
    )
