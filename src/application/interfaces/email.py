from abc import ABC, abstractmethod
from typing import List


class AbstractEmailService(ABC):
    """Interface for email service"""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body: str,
        html: bool = False
    ) -> None:
        """
        Send email
        :param to_email: Recipient email or list of emails
        :param subject: Email subject
        :param body: Email body
        :param html: Is body HTML formatted
        """
        raise NotImplementedError 