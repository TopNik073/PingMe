from collections.abc import Callable
import time
from typing import Any, Literal
import uuid

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    Logs information about the request, execution time, and response status.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/ws"):
            return await call_next(request)

        if "websocket" in request.headers.get("upgrade", "").lower():
            return await call_next(request)

        context = await self.get_context(request)
        await logger.ainfo(
            f"Request started on {request.method} {request.url.path}", context=context
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except ValueError as e:
            await self.create_final_log("failed", request, context, start_time, 400, e)
            raise HTTPException(status_code=400, detail=str(e)) from e

        except HTTPException as e:
            await self.create_final_log("failed", request, context, start_time, e.status_code, e)
            raise

        except Exception as e:
            await self.create_final_log("failed", request, context, start_time, 500, e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

        else:
            response_size = self.get_response_size(response)
            context["response_size"] = response_size

            await self.create_final_log(
                "successful", request, context, start_time, response.status_code
            )

            response.headers["X-TRACE-ID"] = context["trace_id"]
            response.headers["X-PROCESS-TIME"] = context["process_time"]

            return response

    @staticmethod
    def get_response_size(response: Response) -> int:
        try:
            response_size = response.headers.get("Content-Length")
            if response_size:
                return int(response_size)

            if hasattr(response, 'body') and response.body is not None:
                return len(response.body)

            return 0

        except Exception as e:
            logger.warning(
                "Error getting response size: %s",
                e,
            )
            return 0

    @staticmethod
    async def create_final_log(  # noqa: PLR0913
        msg: Literal["successful", "failed"],
        request: Request,
        context: dict,
        start_time: float,
        status: int | str,
        e: Exception | None = None,
    ) -> None:
        process_time = time.perf_counter() - start_time
        process_time = f"{process_time:.4f}"
        context["process_time"] = process_time
        context["response_status"] = status

        if msg == "successful":
            await logger.ainfo(
                f"Request completed {request.method} {request.url.path}", context=context
            )
        else:
            await logger.aerror(
                f"Request failed {request.method} {request.url.path}", context=context, exc_info=e
            )

    @staticmethod
    async def get_context(request: Request) -> dict[str, Any]:
        trace_id = str(uuid.uuid4())
        content_type = request.headers.get('Content-Type', '')
        body = await request.body()
        body = 'Not available for multipart/form-data' if 'multipart/form-data' in content_type else body.decode()

        return {
            "trace_id": trace_id,
            "client": {
                "ip_address": request.client.host,
                "port": request.client.port,
                "user-agent": request.headers.get("User-Agent"),
            },
            "request": {"body": body, "query": str(request.query_params)},
        }