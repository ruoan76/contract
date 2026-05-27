# -*- coding: utf-8 -*-
"""text_extractor OCR 回退（mock，不加载 EasyOCR 模型）"""
from unittest.mock import patch

import pytest

from app.services.ai_review.text_extractor import ExtractedText, _extract_pdf
from pathlib import Path
import asyncio
import fitz


@pytest.mark.asyncio
async def test_pdf_ocr_fallback_when_text_empty(tmp_path):
    """无文字层 PDF 应触发 OCR 并写入 ocr_used。"""
    pdf_path = tmp_path / "scan.pdf"
    doc = fitz.open()
    doc.new_page()  # 无文字层空白页
    doc.save(str(pdf_path))
    doc.close()

    fake_pages = ["甲方：测试公司", "合同金额：100万元"]

    with patch("app.services.ai_review.text_extractor.settings") as mock_settings:
        mock_settings.AI_OCR_ENABLED = True
        mock_settings.AI_OCR_MIN_CHARS = 200
        mock_settings.AI_OCR_PAGE_MIN_CHARS = 50
        mock_settings.AI_OCR_GIBBERISH_RATIO = 0.35
        mock_settings.AI_OCR_MAX_PAGES = 40
        mock_settings.MAX_FILE_SIZE = 50 * 1024 * 1024

        with patch(
            "app.services.ai_review.ocr.ocr_pdf_pages",
            return_value=fake_pages,
        ):
            result = await _extract_pdf(Path(pdf_path), "pdf")

    assert result.metadata.get("ocr_used") is True
    assert "测试公司" in result.full_text
