# -*- coding: utf-8 -*-
"""MLX OpenAI 兼容 API 可达性探测。"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 3.0


def _models_url() -> str:
    base = (settings.AI_BASE_URL or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


async def check_mlx_reachable() -> tuple[bool, str]:
    """
    探测 MLX /v1/models 是否可达。

    Returns:
        (ok, message) — ok 为 False 时 message 含简要原因
    """
    if settings.AI_REVIEW_MOCK:
        return True, "mock mode"

    url = _models_url()
    try:
        async with httpx.AsyncClient(timeout=_CONNECT_TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return False, f"HTTP {resp.status_code}"
            return True, "ok"
    except httpx.ConnectError:
        host = urlparse(url).netloc or settings.AI_BASE_URL
        return False, f"无法连接 {host}"
    except httpx.TimeoutException:
        return False, f"连接超时（>{_CONNECT_TIMEOUT}s）"
    except Exception as exc:
        logger.warning("MLX 预检异常: %s", exc)
        return False, str(exc)


def mlx_unavailable_detail(reason: str = "") -> str:
    """生成面向用户的 MLX 不可用提示。"""
    base = settings.AI_BASE_URL or "127.0.0.1:27366/v1"
    hint = (
        f"MLX 推理服务不可达（{base}）。"
        "请确认 mlx_lm.server 已启动，例如："
        f"mlx_lm.server --model {settings.AI_MODEL} --port 27366"
    )
    if reason:
        return f"{hint}（{reason}）"
    return hint
