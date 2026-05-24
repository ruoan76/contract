"""飞书 Webhook 推送辅助"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_feishu_webhook_sync(text: str, title: Optional[str] = None) -> bool:
    """同步发送飞书文本消息；未配置 webhook 时静默跳过。"""
    url = settings.FEISHU_WEBHOOK_URL
    if not url:
        return False
    content = text if not title else f"**{title}**\n{text}"
    payload = {
        "msg_type": "text",
        "content": {"text": content},
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("飞书 webhook 发送失败: %s", exc)
        return False


async def send_feishu_webhook(text: str, title: Optional[str] = None) -> bool:
    """异步发送飞书文本消息；未配置 webhook 时静默跳过。"""
    url = settings.FEISHU_WEBHOOK_URL
    if not url:
        return False
    content = text if not title else f"**{title}**\n{text}"
    payload = {
        "msg_type": "text",
        "content": {"text": content},
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("飞书 webhook 发送失败: %s", exc)
        return False
