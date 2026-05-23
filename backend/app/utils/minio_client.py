"""
MinIO 对象存储客户端

封装上传、下载、删除、预签名 URL 操作。
客户端实例为全局单例，所有方法均为 async-friendly，
内部通过 run_in_executor 将阻塞 I/O 卸载到线程池。
"""
from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any, BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinIOClient:
    """MinIO 客户端封装"""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool = False,
    ) -> None:
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket = bucket or settings.MINIO_BUCKET
        self.secure = secure
        self._client: Minio | None = None

    @property
    def client(self) -> Minio:
        """懒加载 Minio 实例"""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    # ------------------------------------------------------------------
    # 内部辅助：将阻塞调用放入线程池
    # ------------------------------------------------------------------

    @staticmethod
    async def _run(func: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    # ------------------------------------------------------------------
    # 核心操作
    # ------------------------------------------------------------------

    async def ensure_bucket(self) -> None:
        """确保存储桶存在，不存在则创建"""
        await self._run(self.client.bucket_exists, self.bucket) or await self._run(
            self.client.make_bucket, self.bucket
        )

    async def upload_file(
        self,
        object_name: str,
        file_path: str | BinaryIO | bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, str]:
        """上传文件到 MinIO。

        Args:
            object_name: 对象路径，形如 "contracts/2024/01/file.pdf"。
            file_path: 本地文件路径、类文件对象或字节数据。
            content_type: MIME 类型。

        Returns:
            {"object_name": ..., "bucket": ..., "url": ...}
        """
        await self.ensure_bucket()

        if isinstance(file_path, bytes):
            data = BytesIO(file_path)
            length = len(file_path)
        elif isinstance(file_path, str):
            # 本地文件路径
            await self._run(
                self.client.fput_object,
                self.bucket, object_name, file_path, content_type=content_type
            )
            return {
                "object_name": object_name,
                "bucket": self.bucket,
                "url": f"http://{self.endpoint}/{self.bucket}/{object_name}",
            }
        else:
            data = file_path
            length = None

        await self._run(
            self.client.put_object,
            self.bucket, object_name, data, length=length, content_type=content_type
        )

        return {
            "object_name": object_name,
            "bucket": self.bucket,
            "url": f"http://{self.endpoint}/{self.bucket}/{object_name}",
        }

    async def download_file(
        self,
        object_name: str,
        dest_path: str | None = None,
    ) -> bytes:
        """下载文件内容。

        Args:
            object_name: MinIO 中的对象路径。
            dest_path: 本地目标路径。若不指定则返回 bytes。

        Returns:
            文件内容的 bytes。
        """
        if dest_path:
            await self._run(self.client.fget_object, self.bucket, object_name, dest_path)
            with open(dest_path, "rb") as f:
                return f.read()

        response = await self._run(self.client.get_object, self.bucket, object_name)
        try:
            return await self._run(response.read)
        finally:
            await self._run(response.close)
            await self._run(response.release_conn)

    async def delete_file(self, object_name: str) -> bool:
        """删除指定对象。

        Returns:
            True 表示删除成功。
        """
        await self._run(self.client.remove_object, self.bucket, object_name)
        return True

    async def presigned_url(
        self,
        object_name: str,
        expires: int = 3600,
    ) -> str:
        """生成预签名 URL，用于临时访问。

        Args:
            object_name: 对象路径。
            expires: 有效时间（秒），默认 1 小时。

        Returns:
            预签名 URL 字符串。
        """
        return await self._run(
            self.client.presigned_get_object,
            self.bucket, object_name, expires=expires
        )


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

minio_client = MinIOClient()
