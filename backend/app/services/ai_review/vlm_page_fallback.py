# -*- coding: utf-8 -*-
"""坏页 OCR 兜底 — LLM 转录纠错（可选 VLM 扩展点）。"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.ai_review.ocr_text_utils import gibberish_ratio

logger = logging.getLogger(__name__)

_VLM_TRANSCRIBE_PROMPT = (
    "你是 OCR 转录助手。下面是一页合同扫描件经 OCR 识别的文本，可能含错字、漏字或阅读顺序乱序。"
    "请在不改变法律含义的前提下，输出纠正后的纯文本转录；重点恢复正确阅读顺序与断行，不要改写条款。"
    "不要添加解释、不要 Markdown。"
    "若原文已清晰可读，原样输出即可。"
)


async def maybe_correct_page_text(
    ocr_text: str,
    *,
    avg_confidence: float = 1.0,
    image_bytes: bytes | None = None,
    layout_suspect: bool = False,
) -> tuple[str, bool]:
    """
    低质量页或排版可疑页兜底纠错。
    返回 (文本, 是否经过 LLM 纠正)。
    """
    if not settings.AI_OCR_VLM_FALLBACK:
        return ocr_text, False

    conf_threshold = float(settings.AI_OCR_VLM_CONF_THRESHOLD)
    gibberish = gibberish_ratio(ocr_text)
    needs = (
        layout_suspect
        or avg_confidence < conf_threshold
        or gibberish > 0.25
    )
    if not needs or not ocr_text.strip():
        return ocr_text, False

    # 预留 VLM 图像转录扩展点
    if image_bytes:
        vlm_text = await _try_vlm_transcribe(image_bytes)
        if vlm_text:
            return vlm_text.strip(), True

    corrected = await _llm_correct_text(ocr_text)
    if corrected and corrected.strip() != ocr_text.strip():
        return corrected.strip(), True
    return ocr_text, False


async def _try_vlm_transcribe(image_bytes: bytes) -> str | None:
    """尝试 VLM 页级转录；未安装视觉模型时返回 None。"""
    if not settings.AI_OCR_VLM_MODEL:
        return None
    try:
        # 扩展点：接入 MLX Qwen2-VL 等本地视觉模型
        logger.debug("VLM 转录未配置实现，跳过（model=%s）", settings.AI_OCR_VLM_MODEL)
    except Exception as exc:
        logger.warning("VLM 转录失败: %s", exc)
    return None


async def _llm_correct_text(ocr_text: str) -> str | None:
    """使用现有文本 LLM 做 OCR 纠错兜底。"""
    try:
        from app.services.ai_review.llm_gateway import LLMCallError, get_llm_gateway

        gateway = get_llm_gateway()
        snippet = ocr_text.strip()
        if len(snippet) > 8000:
            snippet = snippet[:8000]
        content, meta = await gateway.complete_json(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"OCR 原文：\n{snippet}\n\n"
                        '请输出 JSON：{"text": "纠正后的纯文本"}'
                    ),
                }
            ],
            system_prompt=_VLM_TRANSCRIBE_PROMPT,
            caller="ocr_page_fallback",
            max_retries=0,
        )
        if not meta.success:
            return None
        if isinstance(content, dict):
            return str(content.get("text") or content.get("content") or "")
        if isinstance(content, str):
            return content
        return str(content) if content else None
    except LLMCallError as exc:
        logger.warning("OCR LLM 兜底失败: %s", exc)
        return None
    except Exception as exc:
        logger.debug("OCR LLM 兜底跳过: %s", exc)
        return None
