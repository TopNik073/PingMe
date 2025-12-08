import enum


class Roles(str, enum.Enum):
    """User roles in conversations"""

    OWNER = 'owner'  # Creator of the conversation, has full control
    ADMIN = 'admin'  # Can manage users and messages
    MEMBER = 'member'  # Regular participant
