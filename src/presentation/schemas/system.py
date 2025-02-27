from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import psutil
import platform

from src.core.config import settings

class ServiceStatus(BaseModel):
    status: str = "ok"
    latency_ms: float | None = None
    version: str | None = None
    details: Dict[str, Any] | None = None

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
    environment: str = Field(default_factory=lambda: "dev" if settings.DEBUG else "prod")
    version: str | None = None
    start_time: datetime | None = None
    uptime_seconds: float | None = None

    database: ServiceStatus
    redis: ServiceStatus
    system: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }
    )