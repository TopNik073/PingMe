import logging
import asyncio
import json
import sys
import uuid
import os
from datetime import datetime
from typing import Optional
from contextvars import ContextVar
from functools import wraps
from logging.handlers import TimedRotatingFileHandler

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
path_var: ContextVar[str] = ContextVar("path", default="")
method_var: ContextVar[str] = ContextVar("method", default="")


class JsonFormatter(logging.Formatter):
    """
    Formats logs in JSON for easy analysis
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(tz=None).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
            
        path = path_var.get()
        if path:
            log_data["path"] = path
            
        method = method_var.get()
        if method:
            log_data["method"] = method
        
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)
            
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
            
        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """
    Standard formatter for text logs with a consistent format
    """
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S,%03d"
        )
    
    def formatTime(self, record, datefmt=None):
        """
        Override the time formatting to add milliseconds
        """
        created_time = datetime.fromtimestamp(record.created)
        if datefmt:
            formatted_time = created_time.strftime(datefmt[:-4])
            msecs = int(record.created % 1 * 1000)
            return formatted_time + f"{msecs:03d}"
        return created_time.strftime("%Y-%m-%d %H:%M:%S,%03d")


def setup_logging() -> None:
    """
    Configures logging for the entire application
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if settings.LOG_FORMAT == "json" and not settings.DEBUG:
        formatter = JsonFormatter()
    else:
        formatter = StandardFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if settings.LOG_FILE:
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = TimedRotatingFileHandler(
            filename=settings.LOG_FILE,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y-%m-%d"
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"File logging enabled: {settings.LOG_FILE}")
    
    for logger_name in ["uvicorn", "uvicorn.access", "fastapi"]:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(console_handler)
        if settings.LOG_FILE:
            logger.addHandler(file_handler)
        logger.propagate = False
    
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding request information to the logging context
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        path_var.set(request.url.path)
        method_var.set(request.method)
        
        self.logger.debug(f"Request started: {request.method} {request.url.path}")
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        self.logger.debug(
            f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}"
        )
        
        return response


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger with the specified name
    """
    return logging.getLogger(name)


def log_function(logger: Optional[logging.Logger] = None):
    """
    Decorator for logging function calls
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__}")
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
                
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"Calling async {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logger.exception(f"Exception in async {func.__name__}: {str(e)}")
                raise
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
        
    return decorator


def init_logging(app: FastAPI) -> None:
    """
    Initializes logging for the FastAPI application
    """
    setup_logging()
    app.add_middleware(LoggingMiddleware)
    
    logger = get_logger(__name__)
    logger.info(
        f"Starting application {settings.APP_NAME} in {settings.DEBUG and 'DEBUG' or 'PRODUCTION'} mode"
    )
