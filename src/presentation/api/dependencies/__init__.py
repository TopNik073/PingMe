from src.presentation.api.dependencies.services import AUTH_SERVICE_DEP
from src.presentation.api.dependencies.services import USER_SERVICE_DEP
from src.presentation.api.dependencies.services import S3_MANAGER_DEP
from src.presentation.api.dependencies.services import CONVERSATION_SERVICE_DEP
from src.presentation.api.dependencies.services import MEDIA_SERVICE_DEP
from src.presentation.api.dependencies.services import FCM_SERVICE_DEP
from src.presentation.api.dependencies.services import MESSAGE_SERVICE_DEP

__all__ = [
    'AUTH_SERVICE_DEP',
    'CONVERSATION_SERVICE_DEP',
    'FCM_SERVICE_DEP',
    'MEDIA_SERVICE_DEP',
    'MESSAGE_SERVICE_DEP',
    'S3_MANAGER_DEP',
    'USER_SERVICE_DEP',
]