"""
Storage utilities - MinIO file storage wrapper.
"""
import asyncio
from io import BytesIO
from typing import Optional
from urllib.parse import urljoin

from fastapi import UploadFile

from app.core.config import settings


class MinIOStorage:
    """
    MinIO object storage wrapper.
    
    Provides async-friendly file operations using a thread pool executor
    for blocking MinIO calls.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: bool = False,
    ) -> None:
        """
        Initialize MinIO client.

        Args:
            endpoint: MinIO endpoint (e.g., "localhost:9000")
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            bucket: Default bucket name
            secure: Use HTTPS if True, HTTP if False
        """
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure
        self._client: Optional[Minio] = None

    @property
    def client(self):
        """Get or create MinIO client instance."""
        from minio import Minio

        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    @staticmethod
    async def _run_in_executor(func, *args, **kwargs):
        """Run blocking function in thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def ensure_bucket(self) -> None:
        """Ensure bucket exists, create if not."""
        try:
            exists = await self._run_in_executor(
                self.client.bucket_exists, self.bucket
            )
            if not exists:
                await self._run_in_executor(
                    self.client.make_bucket, self.bucket
                )
        except Exception as exc:
            if exc.__class__.__name__ == "S3Error":
                # Bucket might have been created by another process
                pass
            else:
                raise

    async def upload_file(
        self,
        file: UploadFile,
        object_name: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file: FastAPI UploadFile object
            object_name: Object key/path in bucket
            content_type: MIME type (auto-detected if None)

        Returns:
            File URL/key
        """
        await self.ensure_bucket()

        # Read file content
        content = await file.read()

        # Set content type
        ct = content_type or file.content_type or "application/octet-stream"

        # Upload
        await self._run_in_executor(
            self.client.put_object,
            self.bucket,
            object_name,
            BytesIO(content),
            len(content),
            content_type=ct,
        )

        return object_name

    async def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_name: Object key/path in bucket

        Returns:
            File content as bytes

        Raises:
            S3Error: If object not found
        """
        try:
            response = await self._run_in_executor(
                self.client.get_object, self.bucket, object_name
            )
            try:
                return await self._run_in_executor(response.read)
            finally:
                await self._run_in_executor(response.close)
                await self._run_in_executor(response.release_conn)
        except Exception as e:
            if getattr(e, "code", None) == "NoSuchKey":
                raise FileNotFoundError(f"Object not found: {object_name}")
            raise

    async def presigned_url(
        self, object_name: str, expires: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access.

        Args:
            object_name: Object key/path in bucket
            expires: URL expiration time in seconds (default: 1 hour)

        Returns:
            Pre-signed URL string
        """
        return await self._run_in_executor(
            self.client.presigned_get_object, self.bucket, object_name, expires
        )

    async def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.

        Args:
            object_name: Object key/path in bucket

        Returns:
            True if successful
        """
        try:
            await self._run_in_executor(
                self.client.remove_object, self.bucket, object_name
            )
            return True
        except Exception as e:
            if getattr(e, "code", None) == "NoSuchKey":
                return False
            raise


# Global instance
_storage: Optional[MinIOStorage] = None


def get_storage() -> MinIOStorage:
    """
    Get or create global MinIO storage instance.

    Returns:
        MinIOStorage instance
    """
    global _storage
    if _storage is None:
        _storage = MinIOStorage()
    return _storage


__all__ = ["MinIOStorage", "get_storage"]
