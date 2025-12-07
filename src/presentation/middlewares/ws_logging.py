import json
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketDisconnect

from src.core.logging import get_logger

logger = get_logger(__name__)

_websocket_contexts: dict[int, dict[str, Any]] = {}


class WebSocketLoggingMiddleware:
    """
    ASGI middleware for logging WebSocket connections and messages.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return

        trace_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        context = {
            "trace_id": trace_id,
            "client": {
                "ip": scope.get("client")[0] if scope.get("client") else None,
                "port": scope.get("client")[1] if scope.get("client") else None,
            },
            "websocket": {
                "path": scope.get("path"),
                "query": scope.get("query_string", b"").decode(),
            },
        }

        conn_key = id(scope)
        _websocket_contexts[conn_key] = {
            "context": context,
            "start_time": start_time,
            "user_id": None,
        }

        async def send_wrapper(message):
            if message["type"] == "websocket.send":
                await self.log_message_sent(message, context)

            await send(message)

        async def receive_wrapper():
            message = await receive()

            if message["type"] == "websocket.receive":
                await self.log_message_received(message, context)

            return message

        await logger.ainfo(
            f"WebSocket connection established: {scope['path']}",
            context=context,
        )

        try:
            await self.app(scope, receive_wrapper, send_wrapper)

        except WebSocketDisconnect:
            pass

        except Exception as e:
            await logger.aerror(
                f"WebSocket error: {scope['path']}",
                exc_info=e,
                context=context,
            )
            raise

        finally:
            duration = time.perf_counter() - start_time
            user_id = _websocket_contexts.get(conn_key, {}).get("user_id")

            context["disconnect"] = {
                "duration_sec": f"{duration:.4f}",
                "user_id": user_id,
            }

            await logger.ainfo(
                f"WebSocket disconnected: {scope['path']}",
                context=context,
            )

            _websocket_contexts.pop(conn_key, None)

    async def log_message_received(self, message, context):
        data = message.get("text") or message.get("bytes")

        if not data:
            return

        entry = {"raw_size": len(data)}

        try:
            json_data = json.loads(data)
            entry["type"] = json_data.get("type", "unknown")
            entry["data"] = json_data
        except Exception:
            entry["type"] = "raw"
            entry["preview"] = data[:200]

        context["message_received"] = entry

        await logger.ainfo(
            "WebSocket message received",
            context=context,
        )

    async def log_message_sent(self, message, context):
        data = message.get("text") or message.get("bytes")

        if not data:
            return

        entry = {"raw_size": len(data)}

        try:
            json_data = json.loads(data)
            entry["type"] = json_data.get("type", "unknown")
            entry["data"] = json_data
        except Exception:
            entry["type"] = "raw"
            entry["preview"] = data[:200]

        context["message_sent"] = entry

        await logger.ainfo(
            "WebSocket message sent",
            context=context,
        )


def set_websocket_user_id(websocket, user_id: str):
    """Set user_id after authentication."""
    scope = getattr(websocket, "_scope", None)
    if not scope:
        return

    conn_key = id(scope)
    if conn_key in _websocket_contexts:
        _websocket_contexts[conn_key]["user_id"] = user_id
