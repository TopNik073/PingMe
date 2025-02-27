from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis.connection import get_redis
from redis.asyncio import Redis

from src.presentation.schemas.system import HealthResponse, ServiceStatus
from src.core.logging import get_logger

router = APIRouter(tags=["System"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    """
    Check the health of the application and its dependencies.
    
    Returns detailed information about the status of all services.
    """
    logger.debug("Processing health check request")
    
    # Get application start time from state
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = None
    
    if start_time:
        uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # Check Redis
    redis_start = datetime.now()
    redis_ok = False
    redis_latency = 0
    
    try:
        logger.debug("Checking Redis connection")
        redis_start = datetime.now()
        redis_ok = await redis.ping()
        redis_latency = (datetime.now() - redis_start).total_seconds() * 1000
        logger.debug(f"Redis ping successful, latency: {redis_latency:.2f}ms")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
    
    # Get Redis version and details
    redis_version = None
    redis_details = None
    try:
        redis_info = await redis.info()
        redis_version = redis_info.get('redis_version')
        redis_details = {
            "used_memory_human": redis_info.get('used_memory_human'),
            "connected_clients": redis_info.get('connected_clients'),
        }
        logger.debug(f"Redis version: {redis_version}")
    except Exception as e:
        logger.error(f"Failed to get Redis info: {str(e)}")
        redis_details = {"error": str(e)}
    
    # Check database
    db_ok = True
    db_latency = 0
    db_version = None
    db_details = None
    
    try:
        logger.debug("Checking database connection")
        db_start = datetime.now()
        result = await db.execute(text("SELECT version();"))
        db_version = result.scalar()
        db_latency = (datetime.now() - db_start).total_seconds() * 1000
        logger.debug(f"Database query successful, latency: {db_latency:.2f}ms")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        db_ok = False
        db_details = {"error": str(e)}
    
    response = HealthResponse(
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime_seconds,
        start_time=start_time,
        database=ServiceStatus(
            status="ok" if db_ok else "error",
            latency_ms=db_latency,
            version=db_version,
            details=db_details
        ),
        redis=ServiceStatus(
            status="ok" if redis_ok else "error",
            latency_ms=redis_latency,
            version=redis_version,
            details=redis_details
        )
    )
    
    logger.info(
        "Health check completed", 
        extra={
            "db_status": "ok" if db_ok else "error",
            "redis_status": "ok" if redis_ok else "error",
            "uptime_seconds": uptime_seconds
        }
    )
    
    return response 