import enum


class ConversationType(str, enum.Enum):
    """Type of conversation between users"""

    DIALOG = 'dialog'  # Conversation between two users
    POLYLOGUE = 'polylogue'  # Group conversation (more than two users)
