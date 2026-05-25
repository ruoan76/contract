"""
Storage utilities — 本地 / MinIO 存储抽象。
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings


class StorageBackend(ABC):
    """文件存储后端抽象。"""

    @abstractmethod
    async def upload_file(
        self,
        file: UploadFile,
        object_name: str,
        content_type: Optional[str] = None,
    ) -> str:
        """上传文件，返回存储路径或 object key。"""

    @abstractmethod
    async def download_file(self, object_name: str) -> bytes:
        """下载文件内容。"""

    @abstractmethod
    async def delete_file(self, object_name: str) -> bool:
        """删除文件。"""

    @abstractmethod
    async def presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """生成临时访问 URL。"""


class LocalStorageBackend(StorageBackend):
    """本地磁盘存储。"""

    def __init__(self, base_path: Optional[str] = None) -> None:
        self.base_path = Path(base_path or settings.FILE_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, object_name: str) -> Path:
        path = self.base_path / object_name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def upload_file(
        self,
        file: UploadFile,
        object_name: str,
        content_type: Optional[str] = None,
    ) -> str:
        content = await file.read()
        target = self._resolve(object_name)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, target.write_bytes, content)
        return str(target)

    async def download_file(self, object_name: str) -> bytes:
        target = self._resolve(object_name)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {object_name}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, target.read_bytes)

    async def delete_file(self, object_name: str) -> bool:
        target = self._resolve(object_name)
        if not target.exists():
            return False
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, target.unlink)
        return True

    async def presigned_url(self, object_name: str, expires: int = 3600) -> str:
        target = self._resolve(object_name)
        return f"file://{target}"


class MinIOStorageBackend(StorageBackend):
    """
    MinIO 对象存储后端（stub 实现，连接失败时由调用方处理）。
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        secure: bool = False,
    ) -> None:
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure
        self._client = None

    @property
    def client(self):
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def ensure_bucket(self) -> None:
        try:
            exists = await self._run_in_executor(
                self.client.bucket_exists, self.bucket
            )
            if not exists:
                await self._run_in_executor(self.client.make_bucket, self.bucket)
        except Exception as exc:
            if exc.__class__.__name__ != "S3Error":
                raise

    async def upload_file(
        self,
        file: UploadFile,
        object_name: str,
        content_type: Optional[str] = None,
    ) -> str:
        await self.ensure_bucket()
        content = await file.read()
        ct = content_type or file.content_type or "application/octet-stream"
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
                raise FileNotFoundError(f"Object not found: {object_name}") from e
            raise

    async def presigned_url(self, object_name: str, expires: int = 3600) -> str:
        return await self._run_in_executor(
            self.client.presigned_get_object, self.bucket, object_name, expires
        )

    async def delete_file(self, object_name: str) -> bool:
        try:
            await self._run_in_executor(
                self.client.remove_object, self.bucket, object_name
            )
            return True
        except Exception as e:
            if getattr(e, "code", None) == "NoSuchKey":
                return False
            raise


# 向后兼容别名
class MinIOStorage(MinIOStorageBackend):
    """Deprecated: 使用 MinIOStorageBackend。"""


_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """按配置返回存储后端实例。"""
    global _storage
    if _storage is None:
        if settings.FILE_STORAGE == "minio":
            _storage = MinIOStorageBackend()
        else:
            _storage = LocalStorageBackend()
    return _storage


__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "MinIOStorageBackend",
    "MinIOStorage",
    "get_storage",
]
