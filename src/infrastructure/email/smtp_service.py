from typing import List
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

from src.infrastructure.email.templates import TwoFactorAuthTemplate
from src.application.interfaces.email import AbstractEmailService
from src.core.config import settings
from src.infrastructure.database.models.users import Users


class SMTPService(AbstractEmailService):
    """SMTP email service implementation"""

    async def _create_connection(self) -> aiosmtplib.SMTP:
        """Create SMTP connection"""
        # Создаем SSL контекст
        ssl_context = ssl.create_default_context()

        # Создаем SMTP клиент
        smtp = aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=False,
            tls_context=ssl_context,
        )

        # Подключаемся и логинимся
        await smtp.connect()
        await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD.get_secret_value())

        return smtp

    def _create_message(
        self,
        to_email: str | List[str],
        subject: str,
        body: str,
    ) -> MIMEMultipart:
        """Create email message"""
        message = MIMEMultipart()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
        message["Subject"] = subject

        message.attach(MIMEText(body, "html"))

        return message

    async def send_email(
        self, to_email: str | List[str], subject: str, body: str, html: bool = False
    ) -> None:
        """Send email via SMTP"""
        message = self._create_message(to_email, subject, body)

        smtp = await self._create_connection()
        try:
            await smtp.send_message(message)
            print("email sent")
        finally:
            await smtp.quit()

    async def send_verification_email(self, user: Users, token: str) -> None:
        """Send verification email"""
        template = TwoFactorAuthTemplate(username=user.name, code=token)
        await self.send_email(
            to_email=user.email, subject=f"Your Code: {token}", body=template.render()
        )
