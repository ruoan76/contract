# -*- coding: utf-8 -*-
"""VLM/LLM 坏页兜底单测。"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_review.vlm_page_fallback import maybe_correct_page_text


@pytest.mark.asyncio
async def test_maybe_correct_skipped_when_disabled() -> None:
    text, changed = await maybe_correct_page_text("测试", avg_confidence=0.1)
    assert text == "测试"
    assert changed is False


@pytest.mark.asyncio
@patch("app.services.ai_review.vlm_page_fallback.settings")
@patch("app.services.ai_review.vlm_page_fallback._llm_correct_text", new_callable=AsyncMock)
async def test_maybe_correct_when_layout_suspect(mock_llm, mock_settings) -> None:
    mock_settings.AI_OCR_VLM_FALLBACK = True
    mock_settings.AI_OCR_VLM_CONF_THRESHOLD = 0.45
    mock_llm.return_value = "根据《合同法》协商一致"
    text, changed = await maybe_correct_page_text(
        "协商一致，根据《合同法》",
        avg_confidence=0.9,
        layout_suspect=True,
    )
    assert changed is True
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.ai_review.vlm_page_fallback.settings")
@patch("app.services.ai_review.vlm_page_fallback._llm_correct_text", new_callable=AsyncMock)
async def test_maybe_correct_when_low_conf(mock_llm, mock_settings) -> None:
    mock_settings.AI_OCR_VLM_FALLBACK = True
    mock_settings.AI_OCR_VLM_CONF_THRESHOLD = 0.45
    mock_llm.return_value = "纠正后文本"
    text, changed = await maybe_correct_page_text("乱码@@@", avg_confidence=0.2)
    assert changed is True
    assert text == "纠正后文本"
