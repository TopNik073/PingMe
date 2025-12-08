"""
Connection Manager for WebSocket connections.

Manages active WebSocket connections, subscriptions to conversations,
and message routing to users and conversations.
"""

from uuid import UUID
from fastapi import WebSocket
import json
import asyncio

from src.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for users.

    Features:
    - Track connections by user_id
    - Track subscriptions to conversations
    - Send messages to specific users or all participants in a conversation
    - Support for multiple connections per user (multiple devices)
    """

    def __init__(self):
        # Map user_id -> set of WebSocket connections
        self.active_connections: dict[UUID, set[WebSocket]] = {}

        # Map conversation_id -> set of user_ids subscribed to this conversation
        self.conversation_subscriptions: dict[UUID, set[UUID]] = {}

        # Map WebSocket -> user_id (for quick lookup)
        self.connection_to_user: dict[WebSocket, UUID] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        """Register a new WebSocket connection for a user"""
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()

            self.active_connections[user_id].add(websocket)
            self.connection_to_user[websocket] = user_id

            logger.info('User %s connected. Total connections: %s', user_id, len(self.active_connections[user_id]))

    async def disconnect(self, websocket: WebSocket) -> UUID | None:
        """Remove a WebSocket connection and return the user_id if found"""
        async with self._lock:
            user_id = self.connection_to_user.pop(websocket, None)

            if user_id and user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)

                # Remove user from all conversation subscriptions if no connections left
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    # Clean up subscriptions
                    for conversation_id in list(self.conversation_subscriptions.keys()):
                        self.conversation_subscriptions[conversation_id].discard(user_id)
                        if not self.conversation_subscriptions[conversation_id]:
                            del self.conversation_subscriptions[conversation_id]

                logger.info(
                    'User %s disconnected. Remaining connections: %s',
                    user_id,
                    len(self.active_connections.get(user_id, set())),
                )

            return user_id

    async def subscribe_to_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        """Subscribe a user to a conversation"""
        async with self._lock:
            if conversation_id not in self.conversation_subscriptions:
                self.conversation_subscriptions[conversation_id] = set()

            self.conversation_subscriptions[conversation_id].add(user_id)
            logger.debug('User %s subscribed to conversation %s', user_id, conversation_id)

    async def unsubscribe_from_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        """Unsubscribe a user from a conversation"""
        async with self._lock:
            if conversation_id in self.conversation_subscriptions:
                self.conversation_subscriptions[conversation_id].discard(user_id)
                if not self.conversation_subscriptions[conversation_id]:
                    del self.conversation_subscriptions[conversation_id]
                logger.debug('User %s unsubscribed from conversation %s', user_id, conversation_id)

    def is_user_online(self, user_id: UUID) -> bool:
        """Check if a user has any active connections"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_online_users(self, user_ids: list[UUID]) -> list[UUID]:
        """Get list of online users from the provided list"""
        return [uid for uid in user_ids if self.is_user_online(uid)]

    async def send_personal_message(self, message: dict, user_id: UUID) -> bool:
        """
        Send a message to a specific user.
        Returns True if message was sent to at least one connection, False otherwise.
        """
        if not self.is_user_online(user_id):
            return False

        message_json = json.dumps(message, default=str)
        sent = False

        # Send to all connections of the user (multiple devices)
        connections = list(self.active_connections.get(user_id, set()))
        for connection in connections:
            try:
                await connection.send_text(message_json)
                sent = True
            except Exception as e:
                logger.warning('Failed to send message to user %s: %s', user_id, e)
                # Connection might be dead, remove it
                await self.disconnect(connection)

        return sent

    async def send_to_conversation(
        self, message: dict, conversation_id: UUID, exclude_user_id: UUID | None = None
    ) -> list[UUID]:
        """
        Send a message to all participants subscribed to a conversation.
        Returns list of user_ids who received the message.
        """
        if conversation_id not in self.conversation_subscriptions:
            return []

        message_json = json.dumps(message, default=str)
        sent_to: list[UUID] = []

        # Get all subscribed users
        subscribed_users = list(self.conversation_subscriptions[conversation_id])

        for user_id in subscribed_users:
            # Skip excluded user (usually the sender)
            if exclude_user_id and user_id == exclude_user_id:
                continue

            if self.is_user_online(user_id):
                connections = list(self.active_connections.get(user_id, set()))
                for connection in connections:
                    try:
                        await connection.send_text(message_json)
                        if user_id not in sent_to:
                            sent_to.append(user_id)
                    except Exception as e:
                        logger.warning(
                            'Failed to send message to user %s in conversation %s: %s', user_id, conversation_id, e
                        )
                        await self.disconnect(connection)

        return sent_to

    async def broadcast_to_conversation_participants(
        self, message: dict, participant_ids: list[UUID], exclude_user_id: list[UUID] | None = None
    ) -> list[UUID]:
        """
        Broadcast a message to a list of participants.
        Useful when you have participant list from database but they might not be subscribed yet.
        Returns list of user_ids who received the message.
        """
        message_json = json.dumps(message, default=str)
        sent_to: list[UUID] = []

        for user_id in participant_ids:
            if exclude_user_id and user_id in exclude_user_id:
                continue

            if self.is_user_online(user_id):
                connections = list(self.active_connections.get(user_id, set()))
                for connection in connections:
                    try:
                        await connection.send_text(message_json)
                        if user_id not in sent_to:
                            sent_to.append(user_id)
                    except Exception as e:
                        logger.warning('Failed to broadcast message to user %s: %s', user_id, e)
                        await self.disconnect(connection)

        return sent_to

    def get_user_connections_count(self, user_id: UUID) -> int:
        """Get the number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
