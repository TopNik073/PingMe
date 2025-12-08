import asyncio
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID
import boto3
from fastapi import UploadFile

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class S3Manager:
    def __init__(self):
        self.bucket = settings.S3_BUCKET
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY.get_secret_value(),
        )

    async def upload_file(
        self, file: UploadFile | BinaryIO, file_path: str, content_type: str | None = None, public_read: bool = False
    ) -> dict | None:
        """
        Загружает файл в S3 хранилище (async)

        Args:
            file: Файл для загрузки
            file_path: Путь к файлу в бакете
            content_type: MIME-тип файла
            public_read: Если True, файл будет доступен публично (ACL='public-read')
        """
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name

                if isinstance(file, UploadFile):
                    content = await file.read()
                    temp_file.write(content)
                else:
                    content = file.read()
                    temp_file.write(content)
                    file.seek(0)

            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if public_read:
                extra_args['ACL'] = 'public-read'

            await asyncio.to_thread(
                self.s3_client.upload_file,
                temp_file_path,
                self.bucket,
                file_path,
                ExtraArgs=extra_args if extra_args else {},
            )

            size = Path(temp_file_path).stat().st_size

            Path(temp_file_path).unlink()
            temp_file_path = None

            file_url = f'{settings.S3_ENDPOINT}/{self.bucket}/{file_path}'
            return {
                'name': file_path.split('/')[-1],
                'url': file_url,
                'path': file_path,
                'size': size,
                'mime_type': content_type,
                'uploaded_at': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.exception('Error uploading file to S3: %s', e)
            if temp_file_path and Path(temp_file_path).exists():
                with suppress(Exception):
                    Path(temp_file_path).unlink()
            return None

    async def upload_files(self, files: list[UploadFile | BinaryIO], base_path: str) -> list[dict]:
        """
        Загружает несколько файлов в S3 (async)
        """
        uploaded_files = []
        for file in files:
            filename = None
            content_type = None

            if isinstance(file, UploadFile):
                filename = file.filename
                content_type = file.content_type
            elif hasattr(file, 'filename'):
                filename = file.filename
                content_type = getattr(file, 'content_type', None)

            if filename:
                file_path = f'{base_path}/{filename}'
                result = await self.upload_file(file, file_path, content_type)
                if result:
                    uploaded_files.append(result)
        return uploaded_files

    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str | None:
        """
        Генерирует временный URL для доступа к файлу (async)

        Args:
            file_path: Путь к файлу в бакете
            expires_in: Время жизни URL в секундах

        Returns:
            URL для доступа к файлу или None при ошибке
        """
        try:
            url = await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_path},
                ExpiresIn=expires_in,
            )
            return url  # noqa: RET504
        except Exception as e:
            logger.exception('Error generating presigned URL: %s', e)
            return None

    async def delete_file(self, file_path: str) -> bool:
        """
        Удаляет файл из S3 (async)

        Args:
            file_path: Путь к файлу в бакете

        Returns:
            True если удаление успешно, False при ошибке
        """
        try:
            await asyncio.to_thread(self.s3_client.delete_object, Bucket=self.bucket, Key=file_path)
            return True
        except Exception as e:
            logger.exception('Error deleting file from S3: %s', e)
            return False

    async def delete_files(self, file_paths: list[str]) -> bool:
        """
        Удаляет несколько файлов из S3 (async)

        Args:
            file_paths: Список путей к файлам

        Returns:
            True если все файлы удалены успешно
        """
        try:
            objects = [{'Key': path} for path in file_paths]
            await asyncio.to_thread(self.s3_client.delete_objects, Bucket=self.bucket, Delete={'Objects': objects})
            return True
        except Exception as e:
            logger.exception('Error deleting files from S3: %s', e)
            return False

    async def download_file(self, file_path: str) -> tuple[bytes, str, int] | None:
        """
        Скачивает файл из S3 и возвращает содержимое и метаданные (async)

        Args:
            file_path: Путь к файлу в бакете

        Returns:
            Кортеж (file_content: bytes, content_type: str, size: int) или None при ошибке
        """
        try:
            response = await asyncio.to_thread(self.s3_client.get_object, Bucket=self.bucket, Key=file_path)

            file_content = response['Body'].read()

            content_type = response.get('ContentType', 'application/octet-stream')
            size = response.get('ContentLength', len(file_content))

            return file_content, content_type, size
        except Exception as e:
            logger.exception('Error downloading file from S3: %s', e)
            return None

    async def create_folder(self, conversation_id: UUID) -> bool:
        """
        Creates a "folder" in S3 for a chat (empty object with key {conversation_id}/)

        Args:
            conversation_id: ID чата

        Returns:
            True если создание успешно, False при ошибке
        """
        try:
            folder_path = f'{conversation_id}/'
            await asyncio.to_thread(self.s3_client.put_object, Bucket=self.bucket, Key=folder_path, Body=b'')
            logger.info('Created S3 folder for conversation %s', conversation_id)
            return True
        except Exception as e:
            logger.exception('Error creating S3 folder for conversation %s: %s', conversation_id, e)
            return False
