"""
FCM Service - Firebase Cloud Messaging integration.

Sends push notifications to offline users when they receive messages.
"""

from uuid import UUID
import asyncio

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    messaging = None

from src.infrastructure.database.repositories.user_repository import UserRepository
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class FCMService:
    """
    Firebase Cloud Messaging service for sending push notifications.
    
    Note: This is a basic structure. Full implementation requires:
    - Firebase Admin SDK setup
    - Credentials configuration
    - Message formatting
    """
    
    def __init__(self, user_repository: UserRepository):
        self._user_repo = user_repository
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize FCM service with credentials.
        
        Returns True if initialization successful, False otherwise.
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("firebase-admin not installed. FCM push notifications disabled.")
            return False
        
        # Check if already initialized
        try:
            firebase_admin.get_app()
            logger.info("Firebase Admin SDK already initialized")
            self._initialized = True
            return True
        except ValueError:
            # Not initialized yet, continue
            pass
        
        # Get credentials file path
        creds_path = settings.FCM_CREDENTIALS_FILE
        if not creds_path or not creds_path.exists():
            logger.warning(
                "FCM credentials file not found at %s. Push notifications disabled.",
                creds_path,
            )
            return False
        
        try:
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(str(creds_path))
            firebase_admin.initialize_app(cred)
            self._initialized = True
            logger.info("FCM service initialized successfully with credentials from %s", creds_path)
            return True
        except Exception as e:
            logger.error("Failed to initialize FCM service: %s", e)
            self._initialized = False
            return False
    
    async def send_notification(  # noqa: PLR0911
        self,
        user_id: UUID,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Send a push notification to a user.
        
        Args:
            user_id: Target user ID
            title: Notification title
            body: Notification body
            data: Additional data payload
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self._initialized:
            logger.debug("FCM not initialized, skipping notification to user %s", user_id)
            return False
        
        if not FIREBASE_AVAILABLE:
            logger.debug("FCM library not available, skipping notification to user %s", user_id)
            return False
        
        try:
            # Get user's FCM token
            user = await self._user_repo.get_by_id(user_id)
            if not user:
                logger.warning("User %s not found when sending FCM notification", user_id)
                return False
                
            if not user.fcm_token:
                logger.debug("User %s has no FCM token", user_id)
                return False
            
            # Prepare data payload (convert all values to strings as required by FCM)
            data_payload = {}
            if data:
                for key, value in data.items():
                    data_payload[str(key)] = str(value)
            
            # Create FCM message
            message = messaging.Message(
                token=user.fcm_token,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data_payload,
                android=messaging.AndroidConfig(
                    priority="high",
                ),
                apns=messaging.APNSConfig(
                    headers={
                        "apns-priority": "10",
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
            )
            
            # Send notification (run in thread pool since messaging.send is blocking)
            response = await asyncio.to_thread(messaging.send, message)
            logger.info("FCM notification sent to user %s, message ID: %s", user_id, response)
            return True
            
        except messaging.UnregisteredError as e:
            # Token is invalid or unregistered, remove it
            logger.warning(
                "FCM token for user %s is invalid or unregistered. Removing token. Error: %s",
                user_id,
                e,
            )
            try:
                user = await self._user_repo.get_by_id(user_id)
                if user:
                    user.fcm_token = None
                    await self._user_repo.commit()
                    logger.info("Removed invalid FCM token for user %s", user_id)
            except Exception as cleanup_error:
                logger.error(
                    "Failed to remove invalid FCM token for user %s: %s",
                    user_id,
                    cleanup_error,
                )
            return False
        except messaging.InvalidArgumentError as e:
            logger.error(
                "Invalid FCM message argument for user %s: %s. Message data: title='%s', body length=%s",
                user_id,
                e,
                title,
                len(body),
            )
            return False
        except messaging.SenderIdMismatchError as e:
            logger.error("FCM sender ID mismatch for user %s: %s", user_id, e)
            return False
        except Exception as e:
            logger.exception(
                "Failed to send FCM notification to user %s: %s. Error type: %s",
                user_id,
                e,
                type(e).__name__,
            )
            return False
    
    async def send_message_notification(
        self,
        user_id: UUID,
        sender_name: str,
        message_content: str,
        conversation_id: UUID,
        message_id: UUID,
    ) -> bool:
        """
        Send a notification about a new message.
        
        Args:
            user_id: Target user ID
            sender_name: Name of the message sender
            message_content: Content of the message
            conversation_id: ID of the conversation
            message_id: ID of the message
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Truncate message content for notification
        MAX_NOTIFICATION_LENGTH = 100
        truncated_content = message_content[:MAX_NOTIFICATION_LENGTH] + "..." if len(message_content) > MAX_NOTIFICATION_LENGTH else message_content
        
        return await self.send_notification(
            user_id=user_id,
            title=f"New message from {sender_name}",
            body=truncated_content,
            data={
                "type": "message",
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
                "sender_name": sender_name,
            },
        )
    
    async def send_batch_notifications(
        self,
        user_ids: list[UUID],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> int:
        """
        Send notifications to multiple users.
        
        Returns:
            Number of successfully sent notifications
        """
        if not self._initialized:
            return 0
        
        success_count = 0
        for user_id in user_ids:
            if await self.send_notification(user_id, title, body, data):
                success_count += 1
        
        return success_count

