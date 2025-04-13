from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone

from src.core.config import settings
from src.core.logging import init_logging, get_logger
from src.infrastructure.database.session import engine
from src.infrastructure.cache.redis.connection import init_redis_pool, close_redis_pool
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

    logger.info("Application started successfully")
    yield

    # Shutdown
    logger.info("Shutting down application")

    # Close connections
    await close_redis_pool(app.state.redis)
    await engine.dispose()

    logger.info("Application shutdown complete")


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# Initialize logging
init_logging(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Here we will connect the routers
app.include_router(V1_ROUTER)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
