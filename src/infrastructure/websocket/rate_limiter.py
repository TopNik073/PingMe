"""
Rate Limiter for WebSocket connections.

Tracks message rates per user to prevent abuse.
"""

import time
from collections import defaultdict
from uuid import UUID

from src.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    
    Tracks requests per user and message type within a time window.
    """
    
    def __init__(
        self,
        messages_per_minute: int = 30,
        typing_per_minute: int = 10,
        general_per_minute: int = 100,
    ):
        self.messages_per_minute = messages_per_minute
        self.typing_per_minute = typing_per_minute
        self.general_per_minute = general_per_minute
        
        # Track requests: user_id -> message_type -> list of timestamps
        self.requests: dict[UUID, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Message type to rate limit mapping
        self.rate_limits: dict[str, int] = {
            "message": messages_per_minute,
            "message_edit": messages_per_minute,
            "message_delete": messages_per_minute,
            "message_forward": messages_per_minute,
            "typing_start": typing_per_minute,
            "typing_stop": typing_per_minute,
            "mark_read": general_per_minute,
            "ping": general_per_minute,
            "auth": 5,  # Limit auth attempts
        }
    
    def is_allowed(self, user_id: UUID, message_type: str) -> bool:
        """
        Check if a request is allowed based on rate limits.
        
        Returns True if allowed, False if rate limit exceeded.
        """
        if not user_id:
            # For unauthenticated requests, use a default limit
            return self._check_rate_limit(None, message_type, self.general_per_minute)
        
        # Get rate limit for this message type (default to general limit)
        limit = self.rate_limits.get(message_type, self.general_per_minute)
        
        return self._check_rate_limit(user_id, message_type, limit)
    
    def _check_rate_limit(
        self, user_id: UUID | None, message_type: str, limit: int
    ) -> bool:
        """Check rate limit for a specific user and message type"""
        now = time.time()
        window_start = now - 60.0  # 1 minute window
        
        # Get request history for this user and message type
        if user_id:
            user_requests = self.requests[user_id][message_type]
        else:
            # For unauthenticated, use a special key
            user_requests = self.requests[UUID("00000000-0000-0000-0000-000000000000")][message_type]
        
        # Remove old requests outside the window
        user_requests[:] = [ts for ts in user_requests if ts > window_start]
        
        # Check if limit exceeded
        if len(user_requests) >= limit:
            logger.warning(
                "Rate limit exceeded for user %s, message type %s: %d/%d",
                user_id, message_type, len(user_requests), limit
            )
            return False
        
        # Record this request
        user_requests.append(now)
        return True
    
    def reset_user(self, user_id: UUID):
        """Reset rate limit counters for a user (e.g., on disconnect)"""
        if user_id in self.requests:
            del self.requests[user_id]

