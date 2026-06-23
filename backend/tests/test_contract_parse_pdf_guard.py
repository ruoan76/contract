# -*- coding: utf-8 -*-
"""合同解析 — 禁止将 PDF 二进制误解码为正文。"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_review.ocr_text_utils import is_pdf_binary_text
from app.services.contract_parse_service import extract_bytes_to_text


def test_is_pdf_binary_text_detects_pdf_header() -> None:
    assert is_pdf_binary_text("%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj") is True


def test_is_pdf_binary_text_normal_contract() -> None:
    assert is_pdf_binary_text("青海烟草新零售系统采购合同\n甲方：青海省烟草公司") is False


@pytest.mark.asyncio
async def test_extract_bytes_rejects_pdf_decode_on_failure() -> None:
    """extract_text 失败时不得把 PDF 字节 decode 成正文。"""
    pdf_like = b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"

    with patch(
        "app.services.contract_parse_service.extract_text",
        new_callable=AsyncMock,
        side_effect=RuntimeError("OCR failed"),
    ):
        with pytest.raises(ValueError, match="PDF/Word 文本提取失败"):
            await extract_bytes_to_text(pdf_like, "合同.pdf", "application/pdf")


@pytest.mark.asyncio
async def test_extract_bytes_rejects_pdf_binary_text_result() -> None:
    """即使 extract 返回 PDF 流样式文本也应拒绝。"""
    fake_meta = {"ocr_used": False}

    class FakeExtracted:
        full_text = "%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj"
        metadata = fake_meta

    with patch(
        "app.services.contract_parse_service.extract_text",
        new_callable=AsyncMock,
        return_value=FakeExtracted(),
    ):
        with pytest.raises(ValueError, match="PDF 原始数据"):
            await extract_bytes_to_text(b"%PDF-1.4", "合同.pdf", "application/pdf")


@pytest.mark.asyncio
async def test_extract_bytes_txt_fallback_still_works() -> None:
    """纯 txt 在 extract 失败时仍可编码回退。"""
    content = "甲方：测试公司\n合同金额：10000元".encode("utf-8")

    with patch(
        "app.services.contract_parse_service.extract_text",
        new_callable=AsyncMock,
        side_effect=RuntimeError("skip"),
    ):
        text, meta = await extract_bytes_to_text(content, "合同.txt", "text/plain")
    assert "测试公司" in text
    assert meta == {}
